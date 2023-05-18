"""
    Functions associated with the evolutionary process are stored here.
"""

import copy
import math
import random

import os

from PIL import Image, ImageDraw, ImageChops
import opensimplex
import tracery
from generative_object import GenerativeObject
from techniques import *
import cv2
from scipy.spatial import distance as dist

from settings import *

args = ""
lexicase_ordering = []
glob_fit_indicies = []

glob_cur_gen = 0

##########################################################################################


class ExperimentSettings(object):
    num_environments = 1
    num_objectives = num_environments * 7  # 4 ways to measure fitness per environment.

    args = ""

    treatments = [
        "baseline",  #0
    ]
    num_objectives = 3

    rules = rules
    grammar = tracery.Grammar(rules)

    DIM = DIM 


##########################################################################################
# Logging Methods
def cleanFitnessFile(filepath, trtmnt=-1, rep=-1, last_gen=-1):
    """ Clean up the fitness file to remove generations that we do not 
        have the population for as we only log every X generations.
    
    Args:
        filepath: what is the base folder to look for the file
        trtment: what treatment number
        rep: what replicate number
        last_gen: how far did we get with logging the population
    
    """
    data = []
    with open(filepath + "/{}_{}_fitnesses.dat".format(trtmnt, rep), "r") as f:
        # Read in the header row.
        data.append(f.readline())

        for line in f.readlines():
            spl_line = line.split(',')

            # Determine if we should stop processing
            # data as we've exceeded the last
            # generation we have data for.
            if int(spl_line) > last_gen:
                break

            data.append(line)

    with open(filepath + "/{}_{}_fitnesses.dat".format(trtmnt, rep), "w") as f:
        for d in data:
            f.write(d)


class Logging(object):
    """ Handle logging of information for evolution. """

    lexicase_information = []

    @classmethod
    def writeLexicaseOrdering(cls, filename):
        """ Write out the ordering of the fitness metrics selected per generation with lexicase. """
        if not os.path.exists(filename):
            # File does not yet exist, write headers.
            with open(filename, "w") as f:
                # Write Headers
                f.write("Gen, Sel_Event, Objective, Individuals, Sel_Ind\n")

        # Write out the information.
        with open(filename, "a") as f:
            for line in cls.lexicase_information:
                f.write(','.join(str(i) for i in line) + "\n")

        # Clear the lexicase information since we wrote it to the file.
        cls.lexicase_information = []

    @classmethod
    def writePopulationInformation(cls, filename, population):
        with open(filename, "w") as f:
            for p in population:
                f.write(f"{p._id} \t {p.fitness.values} \t {p.grammar}\n")


def writeHeaders(filename, num_objectives):
    """ Write out the headers for a logging file. """
    # pass
    with open(filename, "w") as f:
        f.write("Gen,Ind")
        for i in range(num_objectives):
            f.write(",Fit_{}".format(i))
        f.write("\n")


def writeGeneration(filename, generation, individuals):
    """ Write out the fitness information for a generation. """
    # pass
    with open(filename, "a") as f:
        for i, ind in enumerate(individuals):
            f.write(str(generation) + "," + str(i) + ",")
            f.write(",".join(str(f) for f in ind.fitness.values))
            f.write("\n")


##########################################################################################


# Non-class methods specific to the problem at hand.
def initIndividual(ind_class):
    return ind_class(ExperimentSettings.DIM,
                     ExperimentSettings.grammar.flatten("#ordered_pattern#"))


def evaluate_individual(g):
    """ Wrapper to evaluate an individual.  

    Args:
        individual: arguments to pass to the simulation

    Returns:
        image an individual generates
    """
    for technique in g.grammar.split(','):
        _technique = technique.split(":")  # split off parameters
        c = (random.randint(0,
                            255), random.randint(0,
                                                 255), random.randint(0, 255))
        if _technique[0] == 'flow-field':
            flowField(g.image, 1, g.dim[1], g.dim[0], c, _technique[1],
                      _technique[2], _technique[2])
        elif _technique[0] == 'stippled':
            stippledBG(g.image, c, g.dim)
        elif _technique[0] == 'pixel-sort':
            # 1: angle
            # 2: interval
            # 3: sorting algorithm
            # 4: randomness
            # 5: character length
            # 6: lower threshold
            # 7: upper threshold
            g.image = pixelSort(g.image, _technique[1:])

        elif _technique[0] == 'dither':
            if _technique[1] == 'grayscale':
                g.image = convert_grayscale(g.image)
            elif _technique[1] == 'halftone':
                g.image = convert_halftoning(g.image)
            elif _technique[1] == 'dither':
                g.image = convert_dithering(g.image)
            elif _technique[1] == 'primaryColors':
                g.image = convert_primary(g.image)
            else:
                g.image = simpleDither(g.image)
        elif _technique[0] == 'wolfram-ca':
            WolframCA(g.image, _technique[1])
        elif _technique[0] == 'drunkardsWalk':
            drunkardsWalk(g.image, palette=_technique[1])
        elif _technique[0] == 'flow-field-2':
            flowField2(g.image, _technique[1], _technique[2], _technique[3],
                       _technique[4])
        elif _technique[0] == 'circle-packing':
            circlePacking(g.image, _technique[1], _technique[2])

    return g


# Compare each population member to each other population member (this one uses RMS difference)
# and set its fitness to be the greatest 'difference'
def pairwiseComparison(_population):
    maxUniques = 0
    maxDiff = 0.0
    compared = {}
    for p in _population:
        maxUniques = len(set(p.grammar.split(',')))
        psum = 0

        # image is the background color with no changes - weed out
        numblack = count_nonblack_pil(p.image)
        if numblack == 0:
            p.setFitness(0.0)
        else:
            for p2 in _population:
                if p != p2:
                    maxUniques2 = len(set(p2.grammar.split(',')))
                    if maxUniques2 > maxUniques:
                        maxUniques = maxUniques2

                    id1 = "{0}:{1}".format(p._id, p2._id)
                    id2 = "{0}:{1}".format(p2._id, p._id)
                    keys = compared.keys()
                    if not id1 in keys or not id2 in keys:
                        diff = rmsdiff(p.image, p2.image)

                        if (diff > maxDiff):
                            maxDiff = diff
                        compared[id1] = True
                        psum += diff
            psum /= (len(_population) - 1)
            p.setFitness(psum)

    # actual fitness?
    fitnesses = []
    for p in _population:
        try:
            fitness = p.getFitness() / maxDiff
        except ZeroDivisionError:
            print(p._id, maxDiff)#, maxUniques)
            fitness = 0.0
        p.setFitness(fitness)
        fitnesses.append(fitness)

    return fitnesses

def chebyshev(_population):
    maxDiff = 0.0
    compared = {}
    for p in _population:
        psum = 0

        # image is the background color with no changes - weed out
        numblack = count_nonblack_pil(p.image)
        if numblack == 0:
            p.setFitness(0.0)
        else:
            for p2 in _population:
                if p != p2:
                    id1 = "{0}:{1}".format(p._id, p2._id)
                    id2 = "{0}:{1}".format(p2._id, p._id)
                    keys = compared.keys()
                    if not id1 in keys or not id2 in keys:
                        hist1 = cv2.calcHist(np.asarray(p.image), [0,1,2], None, [8,8,8], [0,256,0,256,0,256])
                        hist1 = cv2.normalize(hist1, hist1).flatten()
                        hist2 = cv2.calcHist(np.asarray(p2.image), [0,1,2], None, [8,8,8], [0,256,0,256,0,256])
                        hist2 = cv2.normalize(hist2, hist2).flatten()

                        diff = dist.chebyshev(hist1, hist2)
                        # diff = rmsdiff(p.image, p2.image)

                        if (diff > maxDiff):
                            maxDiff = diff
                        compared[id1] = True
                        psum += diff
            psum /= (len(_population) - 1)
            p.setFitness(psum)

    # aggregate fitness
    fitnesses = []
    for p in _population:
        try:
            fitness = p.getFitness() / maxDiff
        except ZeroDivisionError:
            print(p._id, maxDiff)#, maxUniques)
            fitness = 0.0
        p.setFitness(fitness)
        fitnesses.append(fitness)

    return fitnesses


# Compare each population member's genome to see how many unique genes it has.
# This is a minimization objective as we want to select individuals with a low score since
# we'll keep a count of how many others have the same gene.  It's a histogram for each
# unique copy of a gene.
def uniqueGeneCount(_population):
    genes = {}
    for p in _population:
        ind_genes = p.grammar.split(',')

        # Add the occurences of each gene to the genes dictionary.
        for ig in ind_genes:
            if ig not in genes:
                genes[ig] = 1
            else:
                genes[ig] += 1

    # Tally each individuals scores based on the sweep of genes
    # in the population.
    fitnesses = []
    for p in _population:
        ind_genes = p.grammar.split(',')

        fitnesses.append(0)
        for ig in ind_genes:
            fitnesses[-1] += genes[ig]

    return fitnesses


# Find how many unique techniques and individual has.
def numUniqueTechniques(_population):
    fitnesses = []
    for p in _population:
        techniques = []
        for technique in p.grammar.split(','):
            techniques.append(technique.split(":")[0])
        # print(techniques)
        fitnesses.append(len(set(techniques)))
    return fitnesses


# Perform single-point crossover
def singlePointCrossover(ind1, ind2):
    # children
    c1 = copy.deepcopy(ind1)

    split_grammar1 = ind1.grammar.split(",")
    split_grammar2 = ind1.grammar.split(",")

    if len(split_grammar1) > 1 and len(split_grammar2) > 1:
        # crossover for variable length
        # pick an index each and flop
        xover_idx1 = random.randint(1, len(split_grammar1) - 1)
        xover_idx2 = random.randint(1, len(split_grammar2) - 1)

        new_grammar1 = []
        # up to indices
        for i in range(xover_idx1):
            new_grammar1.append(split_grammar1[i])

        # past indices
        for i in range(xover_idx2, len(split_grammar2)):
            new_grammar1.append(split_grammar2[i])

    else:  # one of the genomes was length 1
        new_grammar1 = []

        if len(split_grammar1) == 1:
            new_grammar1 = copy.deepcopy(split_grammar2)
            new_grammar1.insert(random.randint(0, len(split_grammar2)),
                                split_grammar1[0])
        else:
            new_grammar1 = copy.deepcopy(split_grammar1)
            new_grammar1.insert(random.randint(0, len(split_grammar1)),
                                split_grammar2[0])

    c1.grammar = ",".join(new_grammar1)
    return c1


# And single-point mutation
def singlePointMutation(ind):
    mutator = copy.deepcopy(ind)
    # leaving the 'old' image makes it look neater imo...
    #mutator.image = Image.new("RGBA", DIM, "black")
    # mutator.isEvaluated = False

    # Change a technique.
    if random.random() < 0.25:
        split_grammar = mutator.grammar.split(",")
        mut_idx = random.randint(0, len(split_grammar) - 1)

        # either replace with a single technique or the possibility
        # of recursive techniques
        flattener = "#technique#"
        if random.random() < 0.5:
            flattener = "#techniques#"
        local_grammar = ExperimentSettings.grammar.flatten(flattener)

        split_grammar[mut_idx] = local_grammar
        mutator.grammar = ",".join(split_grammar)
    elif random.random() < 0.9:
        # Mutate an individual technique.
        split_grammar = mutator.grammar.split(",")
        mut_idx = random.randint(0, len(split_grammar) - 1)
        #print("\tMutation Attempt:",split_grammar[mut_idx])
        gene = split_grammar[mut_idx].split(":")
        technique = gene[0]

        # these need to become embedded within the technique itself as a
        # class
        if technique == "pixel-sort":
            gene[1] = str(random.randint(0,
                                         359))  # Mutate the angle of the sort.

            # interval function
            gene[2] = random.choice(
                ['random', 'edges', 'threshold', 'waves', 'none'])
            # sorting function
            gene[3] = random.choice(
                ['lightness', 'hue', 'saturation', 'intensity', 'minimum'])
            # randomness val
            gene[4] = str(round(random.uniform(0.0, 1.0), 2))
            # lower threshold
            gene[5] = str(round(random.uniform(0.0, 0.25), 2))
            # upper threshold
            gene[6] = str(round(random.uniform(0.0, 1.0), 2))

        elif technique == "flow-field":
            gene[1] = random.choice(["edgy", "curves"])
            gene[2] = str(round(random.uniform(0.001, 0.5), 3))
        elif technique == "flow-field-2":
            gene[1] = random.choice(palettes)
            gene[2] = random.choice(["edgy", "curvy"])
            gene[3] = str(random.randint(200, 600))
            gene[4] = str(round(random.uniform(2, 5), 2))
        elif technique == "circle-packing":
            gene[1] = random.choice(palettes)
            gene[2] = str(random.randint(10, 30))

        # no params here - placeholders if we augment
        # elif technique == "stippled":
        #     pass
        # elif technique == "wolfram-ca":
        #     pass
        # elif technique == "drunkardsWalk":
        #     pass
        # elif technique == "dither":
        #     pass

        split_grammar[mut_idx] = ":".join(gene)
        mutator.grammar = ",".join(split_grammar)
    else:
        # Shuffle the order of techniques
        split_grammar = mutator.grammar.split(",")
        random.shuffle(split_grammar)
        mutator.grammar = ",".join(split_grammar)

    return mutator


##########################################################################################


def roulette_selection(objs, obj_wts):
    """ Select a listing of objectives based on roulette selection. """
    obj_ordering = []

    tmp_objs = objs
    tmp_wts = obj_wts

    for i in range(len(objs)):
        sel_objs = [list(a) for a in zip(tmp_objs, tmp_wts)]

        # Shuffle the objectives
        random.shuffle(sel_objs)

        # Generate a random number between 0 and 1.
        ran_num = random.random()

        # Iterate through the objectives until we select the one we want.
        for j in range(len(sel_objs)):
            if sel_objs[j][1] > ran_num:
                obj_ordering.append(sel_objs[j][0])

                # Remove the objective and weight from future calculations.
                ind = tmp_objs.index(sel_objs[j][0])

                del tmp_objs[ind]
                del tmp_wts[ind]

                # Rebalance the weights for the next go around.
                tmp_wts = [k / sum(tmp_wts) for k in tmp_wts]
            else:
                ran_num -= sel_objs[j][1]

    return obj_ordering


def select_elite(population):
    """ Select the best individual from the population by looking at the farthest distance traveled.

    Args:
        population: population of individuals to select from.

    Returns:
        The farthest traveling individual.
    """
    best_ind = population[0]
    dist = population[0].fitness.values[0]

    for ind in population[1:]:
        if ind.fitness.values[0] > dist:
            best_ind = ind
            dist = ind.fitness.values[0]

    return best_ind


def epsilon_lexicase_selection(population,
                               generation,
                               tournsize=4,
                               shuffle=True,
                               prim_shuffle=True,
                               num_objectives=0,
                               epsilon=0.9,
                               excl_indicies=[]):
    """ Implements the epsilon lexicase selection algorithm proposed by LaCava, Spector, and McPhee.

    Selects one individual from a population by performing one individual epsilon lexicase selection event.

    Args:
        population: population of individuals to select from
        generation: what generation is it (for logging)
        tournsize: tournament size for each selection
        shuffle: whether to randomly shuffle the indices
        prim_shuffle: should we shuffle the first objective with the other fit indicies
        excl_indicies: what indicies should we exclude
    Returns:
        An individual selected using the algorithm
    """
    global glob_fit_indicies

    # Get the fit indicies from the global fit indicies.
    fit_indicies = glob_fit_indicies if not shuffle else [
        i for i in range(len(population[0].fitness.weights))
    ]

    # Remove excluded indicies
    if not shuffle:
        fit_indicies = [i for i in fit_indicies if i not in excl_indicies]

    # Shuffle fit indicies if passed to do so.
    if shuffle:
        # Only shuffle "secondary" objectives leaving the first objective always
        # at the forefront.
        if not prim_shuffle:
            fit_indicies = fit_indicies[1:]
            random.shuffle(fit_indicies)
            fit_indicies = [0] + fit_indicies
        else:
            random.shuffle(fit_indicies)

    # Limit the number of objectives as directed.
    if num_objectives != 0:
        fit_indicies = fit_indicies[:num_objectives]

    # Sample the tournsize individuals from the population for the comparison
    sel_inds = random.sample(population, tournsize)

    tie = True

    # Now that we have the indicies, perform the actual lexicase selection.
    # Using a threshold of epsilon (tied if within epsilon of performance)
    for k, fi in enumerate(fit_indicies):
        # Figure out if this is a minimization or maximization problem.
        min_max = (-1 * sel_inds[0].fitness.weights[fi])

        # Rank the individuals based on fitness performance for this metric.
        # Format: fit_value,index in sel_ind,rank

        fit_ranks = [[ind.fitness.values[fi], i, -1]
                     for i, ind in enumerate(sel_inds)]
        fit_ranks = [[i[0], i[1], j] for j, i in enumerate(
            sorted(fit_ranks, key=lambda x: (min_max * x[0])))]

        # Check to see if we're within the threshold value.
        for i in range(1, len(fit_ranks)):
            if math.fabs(fit_ranks[i][0] - fit_ranks[0][0]) / (
                    fit_ranks[0][0] + 0.0000001) < (1.0 - epsilon):
                fit_ranks[i][2] = fit_ranks[0][2]

        # Check to see if we have ties.
        for i in range(1, len(fit_ranks)):
            if fit_ranks[0][2] == fit_ranks[i][2]:
                tie = True
                tie_index = i + 1
            elif i == 1:
                tie = False
                break
            else:
                tie_index = i
                break

        if tie:
            sel_inds = [sel_inds[i[1]] for i in fit_ranks[:tie_index]]
            Logging.lexicase_information.append(
                [generation, k, fi, [ind._id for ind in sel_inds], -1])
        else:
            selected_individual = sel_inds[fit_ranks[0][1]]
            Logging.lexicase_information.append([
                generation, k, fi, [ind._id for ind in sel_inds],
                selected_individual._id
            ])
            tie = False
            break

    # If tie is True, we haven't selected an individual as we've reached a tie state.
    # Select randomly from the remaining individuals in that case.
    if tie:
        selected_individual = random.choice(sel_inds)
        Logging.lexicase_information.append([
            generation, -1, -1, [ind._id for ind in sel_inds],
            selected_individual._id
        ])

    return selected_individual


##########################################################################################


def shuffle_fit_indicies(individual, excl_indicies=[]):
    """ Shuffle the fitness indicies and record them in the lexicase log. 
    
    Args:
        individual: pass one individual so we can get the fitness objectives
        excl_indicies: fitness objectives that are not under selective consideration
    """

    global glob_fit_indicies

    # Get the fitness indicies assigned to an individual
    fit_indicies = [i for i in range(len(individual.fitness.weights))]

    # Remove excluded indicies
    fit_indicies = [i for i in fit_indicies if i not in excl_indicies]

    random.shuffle(fit_indicies)

    glob_fit_indicies = fit_indicies