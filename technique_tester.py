"""
This standalone file is used to ensure the techniques work as expected.
"""
from PIL import Image, ImageDraw
from techniques import *
from time import sleep
from colour_palettes import palettes

from evol_utils import evaluate_individual, initIndividual
from generative_object import GenerativeObject

import random, math

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

# Source: https://stackoverflow.com/a/52879133
def hsv_color_list(image):
  """ Get the list of colors present in an image object by HSV value.  
  """
  # Resize the image if we want to save time.
  #Resizing parameters
  width, height = DIM[0], DIM[1]
  image = image.copy()
  image.thumbnail((width, height), resample=0)
  
  # Good explanation of how HSV works to find complimentary colors.
  # https://stackoverflow.com/a/69880467
  image.convert('HSV')
  
  #image = image.resize((width, height), resample = 0)
  #Get colors from image object
  pixels = image.getcolors(width * height)
  #Sort them by count number(first element of tuple)
  sorted_pixels = sorted(pixels, key=lambda t: t[0])
  
  for color in sorted_pixels:
    print(color)
    
  # Print the total number of pixels.
  print(sum([color[0] for color in sorted_pixels]))
  return sorted_pixels
  
def score_negative_space(image, target_percent=.7, primary_black=True):
  """ Assess how closely the provided image matches the target percentage for negative space. 
  
  Args:
    image: image to analyze
    target_percent: target percentage of negative space in the image
    primary_black: boolean indicating whether the primary color should be black or the top color in the image.
  """
  color_distribution = hsv_color_list(image)
  
  total_pixels = sum([color[0] for color in color_distribution])
  
  negative_space_pixels = 0
  if primary_black:
    # The primary color is black, so the negative space is whatever the distribution of black is.
    for color in color_distribution:
      if color[1] == (0,0,0,255):
        negative_space_pixels = color[0]
        break
  else:
    # The primary color is not black, so the negative space is whatever the distribution of the top color is.
    negative_space_pixels = color[0]
    
  negative_space_percent = negative_space_pixels / total_pixels
  
  return math.fabs(target_percent - negative_space_percent)
  
# Source: https://stackoverflow.com/a/52879133
def score_color_alignment(image, n=3):
  """ Find the dominant color in an image and then identify the n complimentary colors.  
      Returned score will be how closely the n primary colors in the image align with an n
      color palette.  
      
      args:
        image: image to analyze
        n: number of complimentary colors to identify
        
      returns:
        score: how closely the n primary colors in the image align with an n color palette.
  """
  # Resize the image if we want to save time.
  #Resizing parameters
  width, height = 150, 150
  image = image.copy()
  image.thumbnail((width, height), resample=0)
  
  # Good explanation of how HSV works to find complimentary colors.
  # https://stackoverflow.com/a/69880467
  image.convert('HSV')
  
  #image = image.resize((width, height), resample = 0)
  #Get colors from image object
  pixels = image.getcolors(width * height)
  #Sort them by count number(first element of tuple)
  sorted_pixels = sorted(pixels, key=lambda t: t[0])
  
  # Get the most frequent colors
  # Filter out black if it is the dominant color since our background is black.
  top_colors = sorted_pixels[-1*(n+1):]
  if top_colors[-1][1] == (0,0,0,255):
    top_colors = top_colors[:-1]
  else:
    top_colors = top_colors[-(n-1):]
    
  # Sort the colors by hue (ascending).
  top_colors = sorted(top_colors, key=lambda x: x[1][0])
  
  # Assess how closely the three colors hue align with a 60 degree separation.
  # This would be a difference of 85 in the HSV hue value between each color.
  if len(top_colors) > n-1:
    avg_distance = sum([math.fabs(top_colors[i][1][0] - top_colors[(i+1)%n][1][0]) if i != n-1 else math.fabs(255-top_colors[i][1][0] + top_colors[(i+1)%n][1][0]) for i in range(n)])/n
  else:
    avg_distance = 255
  
  return math.fabs(255/n - avg_distance)

# Source: https://stackoverflow.com/a/52879133
def score_triadic_color_alignment(image):
  """ Find the dominant color in an image and then identify the three complimentary colors.  
      Returned score will be how closely the three primary colors in the image align with a triadic
      color palette.  
  """
  # Resize the image if we want to save time.
  #Resizing parameters
  width, height = 150, 150
  image = image.copy()
  image.thumbnail((width, height), resample=0)
  
  # Good explanation of how HSV works to find complimentary colors.
  # https://stackoverflow.com/a/69880467
  image.convert('HSV')
  
  #image = image.resize((width, height), resample = 0)
  #Get colors from image object
  pixels = image.getcolors(width * height)
  #Sort them by count number(first element of tuple)
  sorted_pixels = sorted(pixels, key=lambda t: t[0])
  
  # Get the most frequent colors
  # Filter out black if it is the dominant color since our background is black.
  top_colors = sorted_pixels[-4:]
  if top_colors[-1][1] == (0,0,0,255):
    top_colors = top_colors[:-1]
  else:
    top_colors = top_colors[-2:]
    
  # Sort the colors by hue (ascending).
  top_colors = sorted(top_colors, key=lambda x: x[1][0])
  
  # Assess how closely the three colors hue align with a 60 degree separation.
  # This would be a difference of 85 in the HSV hue value between each color.
  if len(top_colors) > 2:
    avg_distance = sum([math.fabs(top_colors[i][1][0] - top_colors[(i+1)%3][1][0]) if i != 2 else math.fabs(255-top_colors[i][1][0] + top_colors[(i+1)%3][1][0]) for i in range(3)])/3
  else:
    avg_distance = 255
  
  return math.fabs(255/3 - avg_distance)
  
if __name__ == "__main__":
    rng = random.Random(0)
    image = Image.new("RGBA", DIM, background)

    # testing a string-based evaluation
    # _grammar = "dither:simpleDither,flow-field-2:FF4365 00A6A6 EFCA08 F49F0A F08700:edgy:274:4"
    # _grammar = "noise-map:0A2463 3E92CC FFFAFF D8315B 912F40:0.027000000000000003:0.137:0.74,drunkardsWalk:75F4F4 90E0F3 B8B3E9 D999B9 D17B88,wolfram-ca:331E36 41337A 6EA4BF C2EFEB ECFEE8,rgb-shift:0.31:0.3:0.96:-3:-1:0:1:-5:-3,flow-field-2:00B9AE 037171 03312E 02C3BD 009F93:curvy:579:2"
    # _grammar =  "walkers:FB8B24 D90368 820263 14342B 04A777:27:rule,rgb-shift:0.8300000000000001:0.8200000000000001:0.44:-4:-3:-1:-5:-5:-5"
    # runGrammar(_grammar, "TEST.4.png")

    # # Generate 10 test images to see how the scores compared to aesthetic appeal.
    for _ in range(10):
      image = Image.new("RGBA", DIM, background)
      circlePacking(image, rng, random.choice(palettes), random.randrange(10, 30))
      score = score_triadic_color_alignment(image)
      
      neg_score = score_negative_space(image)
      print(neg_score)
      
      image.save(f"circles_{int(neg_score*100)}.png")