# GenerativeGI

Genetic algorithm / novelty search for discovering generative artwork via evolving a grammar-based solution.

## Usage

I used Python 3.8, though it should work for most current versions of Python.

1. Install required libraries: `python3 -m pip install -r requirements.txt`

2. Run: `python3 deap_main.py [args]`

  * Arguments:

      * `"--gens", type=int, default=100, help="Number of generations to run evolution for."`
      * `"--pop_size", type=int, default=100, help="Population size for evolution."`
      * `"--treatment", type=int, default=0, help="Run Number"`
      * `"--run_num", type=int, default=0, help="Run Number"`
      * `"--output_path", type=str, default="./", help="Output path."`
      * `"--lexicase",action="store_true",help="Whether to do normal or Lexicase selection."`
      * `"--shuffle", action="store_true", help="Shuffle the fitness indicies per selection event."`
      * `"--tourn_size", type=int, default=4, help="What tournament size should we go with?"`
    

## Grammar construction

Grammars follow the Tracery rules, starting with `ordered_pattern` and are defined in `settings.py`.

## Adding a new technique

To add a technique for drawing you just have to create a self-contained function that accepts a PIL image as input and either updates that same image or returns a new one (up to you, I have some mixed ways to handle that I think).

Techniques are called via the grammar (in `settings.py`).  Basically, you would just add a new rule to the technique rule (with a colon after - I use that for splitting parameters).

Then if you wanted parameters, you can add them below as a new rule.  Currently the only one that accepts parameters is pixel sort, however I'll expand the flow field in the near future to be different.  Note that, if you want to call a different rule, you need to surround it with a pound sign (so for instance, #technique# would be filled with any of the rules within the technique rule) - Tracery in Python isn't too bad, here's a good ref if you want to play with it at all: https://www.brettwitty.net/tracery-in-python.html

So for instance, if I wanted to add circle packing without parameters (just for testing), I'd do something like this:

In `techniques.py`:

Add:

```python
def circlePacking(img):
  # perform circle packing on img directly
```

In `settings.py`:

Update the grammar rules:
```python
rules = {
...
technique = ['stippled:',
             ...
             'circlePacking:'],
}
```

Then in `main.py` within the `evaluate` function:

```python
def evaluate(g): 
   ...
   elif _technique[0] == 'circlePacking':
       circlePacking(g.image)
```

If you want to add additional parameters check the other examples in the grammar - essentially you create a sub-production and reference that within your technique's declaration.

## Techniques

This section outlines the implemented techniques, their parameters, and how to call them via the grammar.

### Circle Packing

**Parameters**

* Palette
* Limit

#### Grammar Specification

Here we outline the specific techniques and their grammar representation.

### Dithering

Dithers an image using either 'simple' PIL dithering (i.e., grayscale only) or via grayscale / halftone / primary colors / Floyd-Steinberg dithering.

#### Grammar Specification

* `'dither:#ditherType#'
  * `'ditherType': ['grayscale', 'halftone', 'dither', 'primaryColors', 'simpleDither']`

### Drunkard's Walk

Performs our implementation of the Drunkards walk algorithm for allowing particles to walk across the canvas.

#### Grammar Specification

* `'drunkardsWalk:#palette#'`

### Flow Field

First implementation of a particle-based flow field.

**Parameters**

* Particle size
* Particle lifetime
* Zoom level (multX, multY)
* Palette
* Style
  * Edgy
  * Flowy

#### Grammar Specification

* `'flow-field:#flow-field-type#:#flow-field-zoom#'`
  * `'flow-field-type': ['edgy', 'curves']`
  * `'flow-field-zoom': [str(x) for x in np.arange(0.001, 0.5, 0.001)]`

### Flow Field v2

Second implementation of the flow field algorithm 

**Parameters**

* Palette
* Style
  * Edgy
  * Flowy
* Noise Scale
* Resolution

#### Grammar Specification

* `'flow-field-2:#palette#:#flow-field-2-type#:#flow-field-2-noisescale#:#flow-field-2-resolution#'`
  * `'flow-field-2-type': ['edgy','curvy']`
  * `'flow-field-2-noisescale': [str(x) for x in range(200, 600)]`
  * `'flow-field-2-resolution': [str(x) for x in range(2, 5)]`

### Pixel Sort

Pixel sorting algorithm c/o https://github.com/satyarth/pixelsort.

**Parameters**

* Angle
* Interval
  * Random
  * Edges
  * Threshold
  * Waves
  * None
* Sorting
  * Lightness
  * Hue
  * Saturation
  * Intensity
  * Minimum
* Lower Threshold
* Upper Threshold

#### Grammar Specification

* `'pixel-sort:#pixel-sort-angle#:#pixel-sort-interval#:#pixel-sort-sorting#:#pixel-sort-randomness#:#pixel-sort-charlength#:#pixel-sort-lowerthreshold#:#pixel-sort-upperthreshold#',`

  * `'pixel-sort-angle': [str(x) for x in range(0, 360)],`
  * `'pixel-sort-interval': ['random', 'edges', 'threshold', 'waves', 'none'],`
  * `'pixel-sort-sorting': ['lightness', 'hue', 'saturation', 'intensity', 'minimum'],`
  * `'pixel-sort-randomness': [str(x) for x in np.arange(0.0, 1.0, 0.05)],`
  * `'pixel-sort-charlength': [str(x) for x in range(1, 30)],`
  * `'pixel-sort-lowerthreshold': [str(x) for x in np.arange(0.0, 0.25, 0.01)],`
  * `'pixel-sort-upperthreshold': [str(x) for x in np.arange(0.0, 1.0, 0.01)],`

### Stipple

Draws a series of small dots over the image for a texturing effect.  No parameters.

### Wolfram Cellular Automata

Executes a cellular automata algorithm, where the input cell rules are currently randomized between pure random selection and the Wolfram CA rules: https://p5js.org/examples/simulate-wolfram-ca.html.

#### Grammar Specification

* `'wolfram-ca:#palette#'`
