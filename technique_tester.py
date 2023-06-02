"""
This standalone file is used to ensure the techniques work as expected.
"""
from PIL import Image, ImageDraw
from techniques import *
from time import sleep
from colour_palettes import palettes

from evol_utils import evaluate_individual, initIndividual
from generative_object import GenerativeObject

DIM = (1000,1000)
background = "black"

## https://www.codementor.io/@isaib.cicourel/image-manipulation-in-python-du1089j1u
# Open an Image
def open_image(path):
  newImage = Image.open(path)
  return newImage

# Save Image
def save_image(image, path):
  image.save(path, 'png')


# Create a new image with the given size
def create_image(i, j):
  image = Image.new("RGBA", (i, j), background)
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
def convert_grayscale(image):
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
      red =   pixel[0]
      green = pixel[1]
      blue =  pixel[2]

      # Transform to grayscale
      gray = (red * 0.299) + (green * 0.587) + (blue * 0.114)

      # Set Pixel in new image
      pixels[i, j] = (int(gray), int(gray), int(gray))

  # Return new image
  return new


# Create a Half-tone version of the image
def convert_halftoning(image):
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
         pixels[i, j]         = (255, 255, 255) # White
         pixels[i, j + 1]     = (255, 255, 255) # White
         pixels[i + 1, j]     = (255, 255, 255) # White
         pixels[i + 1, j + 1] = (255, 255, 255) # White
      elif sat > 159:
         pixels[i, j]         = (255, 255, 255) # White
         pixels[i, j + 1]     = (0, 0, 0)       # Black
         pixels[i + 1, j]     = (255, 255, 255) # White
         pixels[i + 1, j + 1] = (255, 255, 255) # White
      elif sat > 95:
         pixels[i, j]         = (255, 255, 255) # White
         pixels[i, j + 1]     = (0, 0, 0)       # Black
         pixels[i + 1, j]     = (0, 0, 0)       # Black
         pixels[i + 1, j + 1] = (255, 255, 255) # White
      elif sat > 32:
         pixels[i, j]         = (0, 0, 0)       # Black
         pixels[i, j + 1]     = (255, 255, 255) # White
         pixels[i + 1, j]     = (0, 0, 0)       # Black
         pixels[i + 1, j + 1] = (0, 0, 0)       # Black
      else:
         pixels[i, j]         = (0, 0, 0)       # Black
         pixels[i, j + 1]     = (0, 0, 0)       # Black
         pixels[i + 1, j]     = (0, 0, 0)       # Black
         pixels[i + 1, j + 1] = (0, 0, 0)       # Black

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
def convert_dithering(image):
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
      red   = (p1[0] + p2[0] + p3[0] + p4[0]) / 4
      green = (p1[1] + p2[1] + p3[1] + p4[1]) / 4
      blue  = (p1[2] + p2[2] + p3[2] + p4[2]) / 4

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
      pixels[i, j]         = (r[0], g[0], b[0])
      pixels[i, j + 1]     = (r[1], g[1], b[1])
      pixels[i + 1, j]     = (r[2], g[2], b[2])
      pixels[i + 1, j + 1] = (r[3], g[3], b[3])

  # Return new image
  return new


# Create a Primary Colors version of the image
def convert_primary(image):
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
      red =   pixel[0]
      green = pixel[1]
      blue =  pixel[2]

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

# Execute a flattened grammar string
def runGrammar(_grammar, filename):
    # g = initIndividual(GenerativeObject)
    g = GenerativeObject(DIM, _grammar)
    # g.grammar = _grammar
    g = evaluate_individual(g)
    g.image.save(filename)

if __name__ == "__main__":
    random.seed(0)
    image = Image.new("RGBA", DIM, background)

    # WolframCA(image, random.choice(palettes))
    # image = noiseMap(image, random.choice(palettes), random.uniform(0.01, 0.2), random.uniform(0.01, 0.2), random.uniform(0.2,1.0))

    # image = openCV_oilpainting(image, random.randint(1,64))
    # image.save("temp.oil.png")
    # image = openCV_watercolor(image, random.randint(1,200), random.random())
    # image.save("temp.wc.png")
    # image = openCV_pencilSketch(image, random.randint(1,200), random.random(), 0.05, False)#random.choice([True,False]))


    # for i in range(50):
    #   image = Image.new("RGBA", DIM, background)
    #   drawGradient(image, random.choice(palettes), random.randint(1,DIM[1]//8))
      # walkers(image, random.choice(palettes), random.randint(10,100), random.choice(['ordered', 'random', 'rule']))
    #   basic_trig(image, random.choice(palettes), random.randrange(1,100), random.choice(['circle', 'rect']))
    #   r = random.random()
    #   if r < 0.25:
    #     snd = random.randint(1,24)
    #     image = openCV_oilpainting(image, snd)#random.randint(1,64))  ## DOES NOT SEEM TO ACT WELL ON EMPTY SPAC
    #     print(i,0,snd)
    #   elif r < 0.5:
    #     image = openCV_watercolor(image, random.randint(1,200), random.random())
    #     print(i,1)
    #   elif r < 0.75:
    #     image = openCV_pencilSketch(image, random.randint(1,200), random.random(), 0.05, False)#random.choice([True,False]))
    #     print(i,2)
    #   else:
    #     print(i,3)
    # #   image.save("sin2/temp.sin.{0}.png".format(i))
    #   image.save("w/temp.walkers.{0}.png".format(i))
      # image.save('g/gradients.{0}.png'.format(i))

    # testing a string-based evaluation
    # _grammar = "dither:simpleDither,flow-field-2:FF4365 00A6A6 EFCA08 F49F0A F08700:edgy:274:4"
    # _grammar = "noise-map:0A2463 3E92CC FFFAFF D8315B 912F40:0.027000000000000003:0.137:0.74,drunkardsWalk:75F4F4 90E0F3 B8B3E9 D999B9 D17B88,wolfram-ca:331E36 41337A 6EA4BF C2EFEB ECFEE8,rgb-shift:0.31:0.3:0.96:-3:-1:0:1:-5:-3,flow-field-2:00B9AE 037171 03312E 02C3BD 009F93:curvy:579:2"
    _grammar =  "walkers:FB8B24 D90368 820263 14342B 04A777:27:rule,rgb-shift:0.8300000000000001:0.8200000000000001:0.44:-4:-3:-1:-5:-5:-5"
    runGrammar(_grammar, "TEST.4.png")

