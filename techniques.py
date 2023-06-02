from PIL import Image, ImageDraw, ImageChops, ImageColor
import opensimplex
from perlin_noise import PerlinNoise
from pixelsort import pixelsort
# import random
import math
import numpy as np
from settings import *
import scipy.spatial
import cv2
from sklearn.cluster import KMeans


### Utility functions
# map function similar to p5.js
def p5map(n, start1, stop1, start2, stop2):
    return ((n - start1) / (stop1 - start1)) * (stop2 - start2) + start2


# constrain value to range
def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))


# https://stackoverflow.com/questions/3098406/root-mean-square-difference-between-two-images-using-python-and-pil
def rmsdiff(im1, im2):
    "Calculate the root-mean-square difference between two images"
    diff = ImageChops.difference(im1, im2)
    h = diff.histogram()
    sq = (value * ((idx % 256)**2) for idx, value in enumerate(h))
    sum_of_squares = sum(sq)
    rms = math.sqrt(sum_of_squares / float(im1.size[0] * im1.size[1]))
    return rms


# c/o https://codereview.stackexchange.com/questions/55902/fastest-way-to-count-non-zero-pixels-using-python-and-pillow
def count_nonblack_pil(img):
    bbox = img.getbbox()
    if not bbox: return 0
    return sum(
        img.crop(bbox).point(lambda x: 255
                             if x else 0).convert("L").point(bool).getdata())


###


def pixelSort(img, rng, params):
    return pixelsort(
        img,
        angle=int(params[0]),
        interval_function=params[1],
        sorting_function=params[2],
        randomness=float(params[3]),
        #        char_length=float(params[4]),
        lower_threshold=float(params[5]),
        upper_threshold=float(params[6]))
    """
        image: Image.Image,
        mask_image: typing.Optional[Image.Image] = None,
        interval_image: typing.Optional[Image.Image] = None,
        randomness: float = DEFAULTS["randomness"],
        char_length: float = DEFAULTS["char_length"],
        sorting_function: typing.Literal["lightness", "hue", "saturation", "intensity", "minimum"] = DEFAULTS[
            "sorting_function"],
        interval_function: typing.Literal["random", "threshold", "edges", "waves", "file", "file-edges", "none"] =
        DEFAULTS["interval_function"],
        lower_threshold: float = DEFAULTS["lower_threshold"],
        upper_threshold: float = DEFAULTS["upper_threshold"],
        angle: float = DEFAULTS["angle"]
    """


# "simple" PIL dithering
def simpleDither(img, rng):
    dithered = img.convert(mode="1")
    dithered = dithered.convert("RGBA")
    return dithered


# "Simple" Drunkards walk
def drunkardsWalk(
        img,
        rng,
        palette=None,
        pointSize=1,
        life=None,
        startX=None,
        startY=None,
        #   col=None,
        numSteps=None):
    # randomly set parameters if not specified
    if startX == None:
        startX = rng.randint(0, img.width - 1)
        startX = rng.randint(0, img.width - 1)

    if startY == None:
        startY = rng.randint(0, img.height - 1)

    if life == None:
        life = rng.randint(int(img.width * 0.5), int(5 * img.width))

    if palette == None:
        r = rng.randint(0, 255)
        g = rng.randint(0, 255)
        b = rng.randint(0, 255)
        a = rng.randint(20, 255)
        col = (r, g, b, a)
    else:
        palette = getPaletteValues(palette)
        rng.shuffle(palette)
        col = palette[0]

    if numSteps == None:
        numSteps = rng.randint(5, 200)

    draw = ImageDraw.Draw(img)

    # directions [x, y]
    dirs = [
        [-1, -1],  # top left
        [0, -1],  # top 
        [1, -1],  # top right
        [-1, 0],  # middle left
        [0, 0],  # middle 
        [1, 0],  # middle right
        [-1, 1],  # bottom left
        [0, 1],  # bottom 
        [1, 1],  # bottom right
    ]

    l = 0
    x = startX
    y = startY
    while numSteps > 0:
        d = rng.choice(dirs)
        while l < life:
            draw.rectangle([x, y, x + pointSize, y + pointSize], fill=col)

            # allow the drunkard to keep walking to 'branch' out a bit
            if (rng.random() > 0.75):
                d = rng.choice(dirs)
            x += d[0]
            y += d[1]

            x = constrain(x, 0, img.width)
            y = constrain(y, 0, img.height)
            l += 1

        numSteps -= 1
        l = 0

        if (rng.random() > 0.85):
            startX = rng.randint(0, img.width - 1)
            startY = rng.randint(0, img.height - 1)

            # new color!
            rng.shuffle(palette)
            col = palette[0]

        x = startX
        y = startY

    return


def stippledBG(img, rng, fill, DIM):
    draw = ImageDraw.Draw(img)
    for y in range(img.height):
        num = int(img.width * p5map(y, 0, img.height, 0.01, 0.2))
        for _ in range(num):
            x = rng.randint(0, img.width - 1)
            draw.point((x, y), fill)


# Noise from opensimplex.noise returns [-1,1]
def flowField(img,
              rng,
              cellsize,
              numrows,
              numcols,
              fill,
              flowType,
              multX=0.01,
              multY=0.01):
    # unpack the string
    multX = float(multX)
    multY = float(multY)

    draw = ImageDraw.Draw(img)
    grid = []
    for r in range(numrows):
        grid.append([])
        for c in range(numcols):
            n = opensimplex.noise2(x=c * multX, y=r * multY)

            if (flowType == "curves"):
                grid[r].append(p5map(n, -1.0, 1.0, 0.0, 2.0 * math.pi))
            else:
                grid[r].append(
                    math.ceil((p5map(n, 0.0, 1.0, 0.0, 2.0 * math.pi) *
                               (math.pi / 4.0)) / (math.pi / 4.0)))

    particles = []
    for _ in range(1000):
        p = {
            'x': rng.randint(0, numcols - 1),
            'y': rng.randint(0, numrows - 1),
            'life': rng.randint(numcols / 2, numcols)
        }
        particles.append(p)

    while len(particles) > 0:
        #print(len(particles))
        for i in range(len(particles) - 1, -1, -1):
            p = particles[i]
            draw.point((p['x'], p['y']), fill)

            angle = grid[int(p['y'])][int(p['x'])]

            p['x'] += math.cos(angle)
            p['y'] += math.sin(angle)
            p['life'] -= 1
            # print(p)

            if (p['x'] < 0 or p['x'] > numcols - 1 or p['y'] < 0
                    or p['y'] > numrows - 1 or p['life'] <= 0):
                particles.pop(i)
    return


# Based on https://p5js.org/examples/simulate-wolfram-ca.html
def WolframCARules(a, b, c, ruleset):
    if a == 1 and b == 1 and c == 1: return ruleset[0]
    if a == 1 and b == 1 and c == 0: return ruleset[1]
    if a == 1 and b == 0 and c == 1: return ruleset[2]
    if a == 1 and b == 0 and c == 0: return ruleset[3]
    if a == 0 and b == 1 and c == 1: return ruleset[4]
    if a == 0 and b == 1 and c == 0: return ruleset[5]
    if a == 0 and b == 0 and c == 1: return ruleset[6]
    if a == 0 and b == 0 and c == 0: return ruleset[7]
    return 0


def WolframCAGenerate(cells, generation, ruleset):
    nextgen = [0 for _ in range(len(cells))]
    for i in range(1, len(cells) - 1):
        left = cells[i - 1]
        middle = cells[i]
        right = cells[i + 1]
        nextgen[i] = WolframCARules(left, middle, right, ruleset)
    #cells = nextgen
    generation += 1
    return nextgen, generation


    # get list of hex values
def getPaletteValues(p):
    palette = p.split(" ")
    for i, hex in enumerate(palette):
        palette[i] = "#" + hex
    return palette


def WolframCA(img, rng, palette):
    # setup
    draw = ImageDraw.Draw(img)

    palette = getPaletteValues(palette)
    rng.shuffle(palette)
    main_col = palette[0]

    width, height = img.size
    w = 10
    h = (height // w) + 1
    cells = []
    generation = 0

    num_cells = (width // w) + 1
    cells = [0 for _ in range(num_cells)]

    # random starting point
    # TBD param
    if rng.random() > 0.5:
        cells[len(cells) // 2] = 1
    else:
        cells[rng.randint(0, len(cells) - 1)] = 1

    # standard wolfram rules
    # TBD param
    if rng.random() > 0.5:
        ruleset = [0, 1, 0, 1, 1, 0, 1, 0]
    else:
        # rng rules
        ruleset = []
        for _ in range(8):
            ruleset.append(rng.choice([0, 1]))

    # draw and iterate
    col = (220, 220, 220)
    while generation < h:
        for i in range(len(cells)):
            x = i * w
            y = generation * w
            if cells[i] == 1:
                col = main_col  #(220, 0, 220)
            else:
                col = (0, 0, 0)
            draw.rectangle([x, y, x + w, y + w], fill=col)

        cells, generation = WolframCAGenerate(cells, generation, ruleset)
    return


def flowField2(img, rng, palette, flowtype, noisescale, resolution):
    draw = ImageDraw.Draw(img)

    # unpack strings
    noisescale = int(noisescale)
    resolution = int(resolution)

    # get list of hex values
    palette = getPaletteValues(palette)
    # palette = palette.split(" ")
    # for i, hex in enumerate(palette):
    #     palette[i] = "#" + hex

    particles = []
    noise = PerlinNoise()

    # add particles along top and bottom
    for x in range(0, img.width, resolution):
        r = rng.random()
        if r < 0.5:
            p = {'x': x, 'y': 0, 'colour': rng.choice(palette)}
            particles.append(p)
        else:
            p = {'x': x, 'y': img.height, 'colour': rng.choice(palette)}
            particles.append(p)
        x += resolution

    # add particles along left and right sides
    for y in range(0, img.height, resolution):
        r = rng.random()
        if r < 0.5:
            p = {'x': 0, 'y': y, 'colour': rng.choice(palette)}
            particles.append(p)
        else:
            p = {'x': img.width, 'y': y, 'colour': rng.choice(palette)}
            particles.append(p)
        y += resolution

    while len(particles) > 0:
        for i in range(len(particles) - 1, -1, -1):
            p = particles[i]

            draw.point((p['x'], p['y']), p['colour'])
            noiseval = noise([p['x'] / noisescale, p['y'] / noisescale])

            if (flowtype == "curvy"):
                angle = p5map(noiseval, -1.0, 1.0, 0.0, math.pi * 2.0)
            if (flowtype == "edgy"):
                angle = math.ceil(
                    p5map(noiseval, -1.0, 1.0, 0.0, math.pi * 2) *
                    (math.pi / 2)) / (math.pi / 2)

            p['x'] += math.cos(angle)
            p['y'] += math.sin(angle)

            # check edge
            if (p['x'] < 0 or p['x'] > img.width or p['y'] < 0
                    or p['y'] > img.height):
                particles.pop(i)
    return


def circlePacking(img, rng, palette, limit):
    draw = ImageDraw.Draw(img)

    # unpack strings
    limit = int(limit)

    # get list of hex values
    palette = getPaletteValues(palette)
    circles = []
    total = 7  # circles to add each loop

    while True:
        count = 0
        failures = 0
        finished = False

        while count < total:
            # rng centerpoint
            x = rng.randrange(img.width)
            y = rng.randrange(img.height)
            valid = True

            for c in circles:
                # distance between new circle centerpoint and existing circle centerpoint
                d = math.dist([x, y], [c['x'], c['y']])

                if d < c['radius'] + 3:
                    valid = False
                    break

            if valid:
                newC = {
                    'x': x,
                    'y': y,
                    'radius': 1,
                    'colour': rng.choice(palette),
                    'growing': True
                }
                circles.append(newC)
                count += 1
            else:
                failures += 1
            if failures >= limit:
                finished = True
                break

        if finished:
            break

        # grow circles, check edges
        for c in circles:
            x = c['x']
            y = c['y']
            radius = c['radius']

            growing = c['growing']

            if growing:
                # check if circle hit canvas edge
                if x + radius >= img.width or x - radius <= 0 or y + radius >= img.height or y - radius <= 0:
                    c['growing'] = False
                else:
                    # check if circle hit other circle
                    for c2 in circles:
                        x2 = c2['x']
                        y2 = c2['y']
                        radius2 = c2['radius']
                        if c != c2:
                            d = math.dist([x, y], [x2, y2])
                            # check if circles hit each other, with small buffer
                            if d - 4 < radius + radius2:
                                c['growing'] = False
                                break
            if growing:
                # grow
                c['radius'] += 1

    # display
    for c in circles:
        x = c['x']
        y = c['y']
        radius = c['radius']

        if radius == 1:
            pass
        else:
            draw.ellipse(xy=(x - radius, y - radius, x + radius, y + radius),
                         fill=c['colour'],
                         width=radius)


# ---

# Dithering c/o
## https://www.codementor.io/@isaib.cicourel/image-manipulation-in-python-du1089j1u

# Create a new image with the given size
def create_image(i, j):
    image = Image.new("RGBA", (i, j), BACKGROUND)
    return image


# Get the pixel from the given image
def get_pixel(image, i, j):
    # Inside image bounds?
    width, height = image.size
    if i > width or j > height:
        return None

    # Get Pixel
    pixel = image.getpixel((i, j))
    return pixel


# Create a Grayscale version of the image
def convert_grayscale(image, rng):
    # Get size
    width, height = image.size

    # Create new Image and a Pixel Map
    new = create_image(width, height)
    pixels = new.load()

    # Transform to grayscale
    for i in range(width):
        for j in range(height):
            # Get Pixel
            pixel = get_pixel(image, i, j)

            # Get R, G, B values (This are int from 0 to 255)
            red = pixel[0]
            green = pixel[1]
            blue = pixel[2]

            # Transform to grayscale
            gray = (red * 0.299) + (green * 0.587) + (blue * 0.114)

            # Set Pixel in new image
            pixels[i, j] = (int(gray), int(gray), int(gray))

    # Return new image
    return new


# Create a Half-tone version of the image
def convert_halftoning(image, rng):
    # Get size
    width, height = image.size

    # Create new Image and a Pixel Map
    new = create_image(width, height)
    pixels = new.load()

    # Transform to half tones
    for i in range(0, width, 2):
        for j in range(0, height, 2):
            # Get Pixels
            p1 = get_pixel(image, i, j)
            p2 = get_pixel(image, i, j + 1)
            p3 = get_pixel(image, i + 1, j)
            p4 = get_pixel(image, i + 1, j + 1)

            # Transform to grayscale
            gray1 = (p1[0] * 0.299) + (p1[1] * 0.587) + (p1[2] * 0.114)
            gray2 = (p2[0] * 0.299) + (p2[1] * 0.587) + (p2[2] * 0.114)
            gray3 = (p3[0] * 0.299) + (p3[1] * 0.587) + (p3[2] * 0.114)
            gray4 = (p4[0] * 0.299) + (p4[1] * 0.587) + (p4[2] * 0.114)

            # Saturation Percentage
            sat = (gray1 + gray2 + gray3 + gray4) / 4

            # Draw white/black depending on saturation
            if sat > 223:
                pixels[i, j] = (255, 255, 255)  # White
                pixels[i, j + 1] = (255, 255, 255)  # White
                pixels[i + 1, j] = (255, 255, 255)  # White
                pixels[i + 1, j + 1] = (255, 255, 255)  # White
            elif sat > 159:
                pixels[i, j] = (255, 255, 255)  # White
                pixels[i, j + 1] = (0, 0, 0)  # Black
                pixels[i + 1, j] = (255, 255, 255)  # White
                pixels[i + 1, j + 1] = (255, 255, 255)  # White
            elif sat > 95:
                pixels[i, j] = (255, 255, 255)  # White
                pixels[i, j + 1] = (0, 0, 0)  # Black
                pixels[i + 1, j] = (0, 0, 0)  # Black
                pixels[i + 1, j + 1] = (255, 255, 255)  # White
            elif sat > 32:
                pixels[i, j] = (0, 0, 0)  # Black
                pixels[i, j + 1] = (255, 255, 255)  # White
                pixels[i + 1, j] = (0, 0, 0)  # Black
                pixels[i + 1, j + 1] = (0, 0, 0)  # Black
            else:
                pixels[i, j] = (0, 0, 0)  # Black
                pixels[i, j + 1] = (0, 0, 0)  # Black
                pixels[i + 1, j] = (0, 0, 0)  # Black
                pixels[i + 1, j + 1] = (0, 0, 0)  # Black

    # Return new image
    return new


# Return color value depending on quadrant and saturation
def get_saturation(value, quadrant):
    if value > 223:
        return 255
    elif value > 159:
        if quadrant != 1:
            return 255

        return 0
    elif value > 95:
        if quadrant == 0 or quadrant == 3:
            return 255

        return 0
    elif value > 32:
        if quadrant == 1:
            return 255

        return 0
    else:
        return 0


# Create a dithered version of the image
def convert_dithering(image, rng):
    # Get size
    width, height = image.size

    # Create new Image and a Pixel Map
    new = create_image(width, height)
    pixels = new.load()

    # Transform to half tones
    for i in range(0, width, 2):
        for j in range(0, height, 2):
            # Get Pixels
            p1 = get_pixel(image, i, j)
            p2 = get_pixel(image, i, j + 1)
            p3 = get_pixel(image, i + 1, j)
            p4 = get_pixel(image, i + 1, j + 1)

            # Color Saturation by RGB channel
            red = (p1[0] + p2[0] + p3[0] + p4[0]) / 4
            green = (p1[1] + p2[1] + p3[1] + p4[1]) / 4
            blue = (p1[2] + p2[2] + p3[2] + p4[2]) / 4

            # Results by channel
            r = [0, 0, 0, 0]
            g = [0, 0, 0, 0]
            b = [0, 0, 0, 0]

            # Get Quadrant Color
            for x in range(0, 4):
                r[x] = get_saturation(red, x)
                g[x] = get_saturation(green, x)
                b[x] = get_saturation(blue, x)

            # Set Dithered Colors
            pixels[i, j] = (r[0], g[0], b[0])
            pixels[i, j + 1] = (r[1], g[1], b[1])
            pixels[i + 1, j] = (r[2], g[2], b[2])
            pixels[i + 1, j + 1] = (r[3], g[3], b[3])

    # Return new image
    return new


# Create a Primary Colors version of the image
def convert_primary(image, rng):
    # Get size
    width, height = image.size

    # Create new Image and a Pixel Map
    new = create_image(width, height)
    pixels = new.load()

    # Transform to primary
    for i in range(width):
        for j in range(height):
            # Get Pixel
            pixel = get_pixel(image, i, j)

            # Get R, G, B values (This are int from 0 to 255)
            red = pixel[0]
            green = pixel[1]
            blue = pixel[2]

            # Transform to primary
            if red > 127:
                red = 255
            else:
                red = 0
            if green > 127:
                green = 255
            else:
                green = 0
            if blue > 127:
                blue = 255
            else:
                blue = 0

            # Set Pixel in new image
            pixels[i, j] = (int(red), int(green), int(blue))

    # Return new image
    return new

# Perform an RGB color shift 
# Separates image into 3 different layers, shifts each by a 
# parameterized amount, and stitches back together
# based on: https://stackoverflow.com/questions/51325224/python-pil-image-split-to-rgb
def RGBShift(image, rng, alphaR=0.5, alphaG=0.5, alphaB=0.5, 
             rXoff=-5, rYoff=-5,
             gXoff=0, gYoff=-5,
             bXoff=5, bYoff=5):

    # split into separate colors
    data = image.getdata()
    r = [(d[0], 0, 0, 255) for d in data]
    g = [(0, d[0], 0, 255) for d in data]
    b = [(0, 0, d[0], 255) for d in data]

    for d in r:
        if d == (0, 0, 0, 255):
            d = (0, 0, 0, 0)
    for d in g:
        if d == (0, 0, 0, 255):
            d = (0, 0, 0, 0)
    for d in b:
        if d == (0, 0, 0, 255):
            d = (0, 0, 0, 0)

    temp_image = Image.new("RGBA", (image.width, image.height), BACKGROUND)

    # https://stackoverflow.com/questions/37584977/translate-image-using-pil
    # [2] - left/right
    # [5] - up/down

    # red channel
    temp_image.putdata(r)
    temp_image = temp_image.transform(temp_image.size, Image.AFFINE, (1, 0, rXoff, 0, 1, rYoff))
    image = Image.blend(image, temp_image, alphaR)

    # green channel
    temp_image.putdata(g)
    temp_image = temp_image.transform(temp_image.size, Image.AFFINE, (1, 0, gXoff, 0, 1, gYoff))
    image = Image.blend(image, temp_image, alphaG)

    # # blue channel
    temp_image.putdata(b)
    temp_image = temp_image.transform(temp_image.size, Image.AFFINE, (1, 0, bXoff, 0, 1, bYoff))
    image = Image.blend(image, temp_image, alphaB)

    return image

# Overlay a noise map to the existing canvas
def noiseMap(image, rng, palette, noiseX, noiseY, alpha):
    temp_image = Image.new("RGBA", (image.width, image.height), BACKGROUND)
    palette = getPaletteValues(palette)
    rng.shuffle(palette)

    bands = []
    for i in range(len(palette)):
        bands.append(p5map(i, 0, len(palette)-1, -0.9, 0.9))

    width, height = image.size

    # loop over image and apply a value based on an even distribution across the palette
    for y in range(height):
        for x in range(width):
            n = opensimplex.noise2(x=x*noiseX, y=y*noiseY)

            # map to a color band between the opensimplex value on [-1,1]
            col = palette[-1]
            for b in range(len(bands)):
                if n < bands[b]:
                    col = palette[b]
                    break

            temp_image.putpixel((x, y), ImageColor.getrgb(col))
    return Image.blend(image, temp_image, alpha)

### OpenCV effects c/o https://towardsdatascience.com/painting-and-sketching-with-opencv-in-python-4293026d78b

# OpenCV oil painting effect
# Note: this is removing and re-adding the alpha channel as passing in an RGBA image seems to break the oilPainting function.
def openCV_oilpainting(image, rng, dynRatio):
    img = np.array(image.convert('RGB'))
    res = cv2.xphoto.oilPainting(img, dynRatio, 1)
    return Image.fromarray(res).convert('RGBA')

# OpenCV watercolor effect
# sigma_s controls the size of the neighborhood. Range 1 - 200
# sigma_r controls the how dissimilar colors within the neighborhood will be averaged. A larger sigma_r results in large regions of constant color. Range 0 - 1
def openCV_watercolor(image, rng, sigma_s, sigma_r):
    img = np.array(image.convert('RGB'))
    res = cv2.stylization(img, sigma_s=sigma_s, sigma_r=sigma_r)
    return Image.fromarray(res).convert('RGBA')

# OpenCV pencil sketch
# sigma_s and sigma_r are the same as in stylization.
# shade_factor is a simple scaling of the output image intensity. The higher the value, the brighter is the result. Range 0 - 0.1
def openCV_pencilSketch(image, rng, sigma_s, sigma_r, shade_factor, is_bw):
    img = np.array(image.convert('RGB'))
    dst_gray, dst_color = cv2.pencilSketch(img, sigma_s=sigma_s, sigma_r=sigma_r, shade_factor=shade_factor) 
    if is_bw == 'on':
        return Image.fromarray(dst_gray).convert('RGBA')
    else:
        return Image.fromarray(dst_color).convert('RGBA')

# OpenCV stipple effect
"""
def compute_color_probabilities(pixels, palette):
    distances = scipy.spatial.distance.cdist(pixels, palette)
    maxima = np.amax(distances, axis=1)
    distances = maxima[:, None] - distances
    summ = np.sum(distances, 1)
    distances /= summ[:, None]
    return distances

def get_color_from_prob(probabilities, palette):
    probs = np.argsort(probabilities)
    i = probs[-1]
    return palette[i]
def randomized_grid(h, w, scale):
    assert (scale > 0)
    r = scale//2
    grid = []
    for i in range(0, h, scale):
        for j in range(0, w, scale):
            y = random.randint(-r, r) + i
            x = random.randint(-r, r) + j
    grid.append((y % h, x % w))
    random.shuffle(grid)
    return grid
def get_color_palette(img, n=8):#20):
    clt = KMeans(n_clusters=n)
    clt.fit(img.reshape(-1, 4))
    return clt.cluster_centers_
def complement(colors):
    return 255 - colors
def create_pointillism_art(image):
    # img = cv2.imread(image_path)
    img = np.array(image)
    radius_width = int(math.ceil(max(img.shape) / 1000))
    palette = get_color_palette(img)
    complements = complement(palette)
    palette = np.vstack((palette, complements))
    canvas = img.copy()
    grid = randomized_grid(img.shape[0], img.shape[1], scale=3)
    
    pixel_colors = np.array([img[x[0], x[1]] for x in grid])
    
    color_probabilities = compute_color_probabilities(pixel_colors, palette)

    for i, (y, x) in enumerate(grid):
            color = get_color_from_prob(color_probabilities[i], palette)
            cv2.ellipse(canvas, (x, y), (radius_width, radius_width), 0, 0, 360, color, -1, cv2.LINE_AA)

    return Image.fromarray(img)
"""

### TO ADD

def basic_trig(image, rng, palette, num_to_draw, drawtype):
    # amplitude, frequency, offset, pointSize):
    half_height = image.height // 2

    draw = ImageDraw.Draw(image)
    palette = getPaletteValues(palette)
    for _ in range(num_to_draw):
        rng.shuffle(palette)
        col = ImageColor.getrgb(palette[0])
        alpha = rng.randint(20,220)
        col_with_alpha = (col[0], col[1], col[2], alpha)

        amplitude = rng.uniform(1.0, half_height)
        frequency = rng.uniform(-100, 100)
        offset  = half_height
        pointSize = rng.randint(1, 5)
        radius = pointSize // 2
        math_fxn = rng.choice([math.sin, math.cos, math.tan])
        for x in range(0, image.width-1):
            y = amplitude * math_fxn(x * frequency) + offset
            y = constrain(y, 0, image.height-1)
            if drawtype == "rect":
                draw.rectangle([x, y, x + pointSize, y + pointSize], fill=col) # works better with other techniques
            elif drawtype == "circle":
                draw.ellipse(xy=(x - radius, y - radius, x + radius, y + radius),
                         fill=col,
                         width=radius)


            # image.putpixel((int(x), int(y)), col_with_alpha)

def walkers(image, rng, palette, num_walkers, walk_type):
    draw = ImageDraw.Draw(image)
    palette = getPaletteValues(palette)
    TIMEOUT = 1000
    pointSize=2

    particles = []
    # ordered
    vel = [rng.choice([-1,0,1]), rng.choice([-1,0,1])]
    while vel[0] == 0 and vel[1] == 0:
        vel = [rng.choice([-1,0,1]), rng.choice([-1,0,1])]

    # rule based
    vel2 = [rng.choice([-1,0,1]), rng.choice([-1,0,1])]
    while vel2[0] == 0 and vel2[1] == 0:
        vel2 = [rng.choice([-1,0,1]), rng.choice([-1,0,1])]

    for _ in range(num_walkers):
        # rng
        if walk_type == 'rng':
            vel = [rng.choice([-1,0,1]), rng.choice([-1,0,1])]
            while vel[0] == 0 and vel[1] == 0:
                vel = [rng.choice([-1,0,1]), rng.choice([-1,0,1])]
        p = {
            'x': rng.randint(0,image.width-1),
            'y': rng.randint(0,image.height-1),
            'vel': vel,
            'next_vel': vel2,
            'life': rng.randint(image.width//2, image.width*2),
            'update': rng.randint(image.width//8, image.width//2),
            'col': rng.choice(palette)
        }
        particles.append(p)

    for i in range(TIMEOUT):
        for p in particles:
            if p['life'] > 0:
                draw.rectangle([p['x'], p['y'], p['x'] + pointSize, p['y'] + pointSize], fill=p['col'])

                p['x'] += p['vel'][0]
                p['y'] += p['vel'][1]
                p['life'] -= 1

                if i > 0:
                    # update if rngly walking and it is time or we're out of bounds
                    if (p['update'] % i == 0 and walk_type == 'rng') or p['x'] < 0 or p['x'] > image.width-1 or p['y'] < 0 or p['y'] > image.height-1:
                        p['x'] = rng.randint(0,image.width-1)
                        p['y'] = rng.randint(0,image.height-1)
                        p['col'] = rng.choice(palette)
                    elif p['update'] % i == 0 and walk_type == 'rule': # flip velocity
                        temp = p['vel']
                        p['vel'] = p['next_vel']
                        p['next_vel'] = temp



def drawGradient(image, rng, palette, thickness):
    draw = ImageDraw.Draw(image)
    palette = getPaletteValues(palette)

    col1 = rng.choice(palette)
    col2 = rng.choice(palette)

    # lerpcolor?
