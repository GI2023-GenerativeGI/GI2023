"""
Entry point for the DEAP implementation of GenerativeGI
"""

import argparse
import json
import os
import random

from copy import deepcopy

import multiprocessing as mpc
import numpy as np

from deap import base
from deap import creator
from deap import tools

from PIL import Image, ImageTk
import tkinter as tk

import evol_utils
from generative_object import GenerativeObject

ids_to_save = []

# Image selection for tkinter
def selectImage(idx):
    global ids_to_save
    ids_to_save.append(idx)

# Accepts a GenerativeObject and iterates over its grammar, performing the technique specified
def evaluate_ind(g):
    return evol_utils.evaluate_individual(g)
    
def getFitnesses(_pop):
    return [[p_c, g_c, u_c, c_c] for p_c, g_c, u_c, c_c in zip(evol_utils.pairwiseComparison(_pop), evol_utils.uniqueGeneCount(_pop), evol_utils.numUniqueTechniques(_pop), evol_utils.chebyshev(_pop))]

# Initial Fitnesses: 
creator.create("Fitness", base.Fitness, weights=([1.0,-1.0, 1.0, 1.0]))
creator.create("Individual", GenerativeObject, fitness=creator.Fitness)

if __name__ == '__main__': 
    ###################################################################### 

    # Process inputs.
    parser = argparse.ArgumentParser()
    parser.add_argument("--gens", type=int, default=100, help="Number of generations to run evolution for.")
    parser.add_argument("--pop_size", type=int, default=100, help="Population size for evolution.")
    parser.add_argument("--treatment", type=int, default=0, help="Run Number")
    parser.add_argument("--run_num", type=int, default=0, help="Run Number")
    parser.add_argument("--output_path", type=str, default="./", help="Output path")
    parser.add_argument("--lexicase",action="store_true",help="Whether to do normal or Lexicase selection.")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle the fitness indicies per selection event.")
    parser.add_argument("--tourn_size", type=int, default=4, help="What tournament size should we go with?")
    parser.add_argument("--human_interaction", action="store_true", help="Activate GUI interaction for user involvement.")
    parser.add_argument("--human_interaction_gens", type=int, default=5, help="Number of generations to solicit user feedback if human_interaction flag is true")
    parser.add_argument("--clear_canvas", action="store_true", help="To clear or not clear canvas during evolutionary operations.")
    args = parser.parse_args()

    # Create output directories if they don't already exist.
    # Treatment Folder
    if not os.path.exists("{}/{}/".format(args.output_path,args.treatment)):
        os.mkdir("{}/{}/".format(args.output_path,args.treatment))

    # Replicate Folder
    if not os.path.exists("{}/{}/{}".format(args.output_path,args.treatment,args.run_num)):
        os.mkdir("{}/{}/{}".format(args.output_path,args.treatment,args.run_num))

    # Write args to file.
    with open("{}/{}/{}/commandline_args.txt".format(args.output_path,args.treatment,args.run_num), 'w') as f:
        json.dump(args.__dict__, f, indent=2)

    evol_utils.args = args

    # Seed only the evolutionary runs.
    random.seed(args.run_num)
    
    # Establish name of the output files and write appropriate headers.
    out_fit_file = "{}/{}/{}/{}_{}_fitnesses.dat".format(args.output_path,args.treatment,args.run_num,args.treatment,args.run_num)
    lex_log_file = "{}/{}/{}/{}_{}_lexicase_ordering_log.dat".format(args.output_path,args.treatment,args.run_num,args.treatment,args.run_num)
    pop_log_file = "{}/{}/{}/{}_{}_population.dat".format(args.output_path,args.treatment,args.run_num,args.treatment,args.run_num)
    
    if os.path.exists(lex_log_file):
        # Remove the lexicase logging file.
        os.remove(lex_log_file)

    evol_utils.writeHeaders(out_fit_file, evol_utils.ExperimentSettings.num_objectives)
    resume_evolution = False
    log_interval = 100 # How many generations between logging genomes.

    # Create the toolbox for setting up DEAP functionality.
    toolbox = base.Toolbox()

    # Define an individual for use in constructing the population.
    toolbox.register("individual", evol_utils.initIndividual, creator.Individual)
    toolbox.register("mutate", evol_utils.singlePointMutation)
    toolbox.register("mate", evol_utils.singlePointCrossover)

    # Create a population as a list.
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Register the evaluation function.
    toolbox.register("evaluate", evaluate_ind)

    # Register the elite selection.
    toolbox.register("select_elite", evol_utils.select_elite)

    if not args.lexicase:
        # Register the selection function.
        toolbox.register("select", evol_utils.epsilon_lexicase_selection, tournsize=args.tourn_size, shuffle=False, num_objectives=1)
    else:
        # Register the selection function.
        toolbox.register("select", evol_utils.epsilon_lexicase_selection, tournsize=args.tourn_size, shuffle=args.shuffle, num_objectives=4, epsilon=0.85)

    # Crossover and mutation probability
    cxpb, mutpb = 0.5, 0.4

    # Setup the population.
    pop = toolbox.population(n=args.pop_size)

    # Request new id's for the population.
    for ind in pop:
        ind.get_new_id()

    # If we have a prior population, use those genomes
    # otherwise run generation 0.
    fitnesses = []

    # Multiprocessing component.
    cores = mpc.cpu_count()
    pool = mpc.Pool(processes=cores-2)
    # pool = mpc.Pool(processes=1)
    toolbox.register("map", pool.map)

    # Slice population if size is over 240.  (OSError on cluster)
    #slices = [0,args.pop_size] if args.pop_size <= 240 else [i for i in range(0,args.pop_size+1,120)]
    #slices = slices+[args.pop_size] if slices[-1] < args.pop_size else slices

    # Run the first set of evaluations.
    pop = toolbox.map(toolbox.evaluate, pop)

    # Calculate fitnesses once all the individuals have generated images.
    # print(type(pop))
    fitnesses = getFitnesses(pop)

    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit
        
    for i in range(len(pop)):
        print(pop[i]._id, pop[i].fitness.values, pop[i].grammar)
        pop[i].image.save("{}/{}/{}/img-{}.png".format(args.output_path,args.treatment,args.run_num,pop[i]._id))

    # Only log fitnesses if we aren't resuming from a prior checkpoint.
    if not resume_evolution:
        # Log the progress of the population. (For Generation 0)
        evol_utils.writeGeneration(out_fit_file,0,pop)

    gen_reached = 1
    for g in range(gen_reached,args.gens):
        glob_cur_gen = g
        if args.lexicase:
            evol_utils.shuffle_fit_indicies(pop[0])

        # Pull out the elite individual to save for later.
        elite = toolbox.select_elite(pop)

        new_inds = [elite]

        # Select the rest of the children either with crossover or cloning.
        for i in range(args.pop_size):
            if random.random() < cxpb:
                # Crossover
                par_1 = toolbox.select(pop,g)
                par_2 = toolbox.select(pop,g)
                new_child = toolbox.mate(par_1, par_2)
                del new_child.fitness.values
                new_inds.append(new_child)
            else:
                # Cloning
                new_inds.append(toolbox.select(pop,g))

        pop = new_inds
        
        pop = [toolbox.clone(ind) for ind in pop]

        # Request new id's for the population.
        for ind in pop:
            ind.get_new_id()

        for mutant in pop:
            toolbox.mutate(mutant)
            del mutant.fitness.values

        pop = toolbox.map(toolbox.evaluate, pop)

        # Calculate fitnesses once all the individuals have generated images.
        fitnesses = getFitnesses(pop)
        for ind, fit in zip(pop, fitnesses):
            ind.fitness.values = fit

        # Periodically dump lexicase information.
        if g % 50 == 0:
            evol_utils.Logging.writeLexicaseOrdering(lex_log_file)
        
        print(("Generation "+str(g)))
        
        # Log the progress of the population.
        evol_utils.writeGeneration(out_fit_file,g,pop)

        # Popup a tkinter gui window and have the user select the 5 'best' images
        if args.human_interaction and g > 0 and ((g % args.human_interaction_gens) == 0):
            root = tk.Tk()
            root.geometry("1000x1000")
            frame = tk.Frame(root)
            root.rowconfigure(0,weight=1)
            root.columnconfigure(0,weight=1)
            frame.grid(row=0,column=0)

            num_imgs_per_row_col = 4
            if args.pop_size > 20:
                num_imgs_per_row_col = 8
            img_width = 1000 // num_imgs_per_row_col


            img_info = []
            for p in pop:
                _img = p.image.resize((img_width, img_width), Image.ANTIALIAS)
                img_info.append([ImageTk.PhotoImage(_img), p._id])

            x = 0
            y = 0
            half_pop = args.pop_size//2
            for img in img_info:
                imgBtn = tk.Button(frame, image=img[0], command=lambda idx=img[1]:selectImage(idx))
                # imgBtn.pack()
                imgBtn.grid(column=x, row=y)
                x += 1
                if x > num_imgs_per_row_col-1:
                    x = 0
                    y += 1

            frame.columnconfigure(tuple(range(half_pop)),weight=1)
            frame.rowconfigure(tuple(range(half_pop)),weight=1)

            root.title("Generation {0}".format(g))
            root.mainloop()

            if len(ids_to_save) > 0:
                pop = [p for p in pop if p._id in ids_to_save]
            else: # not liked - remove all
                print("ERROR - FIXME")
                # pop = toolbox.population(n=args.pop_size)
                # for ind in pop:
                #     ind.get_new_id()

            pop = [toolbox.clone(random.choice(pop)) for _ in range(args.pop_size-len(pop))]
            # for _ in range(args.pop_size - len(pop)):
            #     mutant = toolbox.clone(random.choice(pop))
            for mutant in pop:
                if mutant._id not in ids_to_save:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values

            # Request new id's for the population.
            for ind in pop:
                ind.get_new_id()

            ids_to_save = []




        # Log the population at 100 generation intervals.
        #if g % log_interval == 0:
            #for i, ind in enumerate(pop):
                #ind.save_individual(file_extension=args.output_path, trtmnt=args.treatment, rep=args.run_num, gen=g, ind=i)

    # Get the final elite individual.
    elite = toolbox.select_elite(pop)
    print(elite._id, elite.fitness.values)
    # elite.save_individual(file_extension=args.output_path, trtmnt=args.treatment, rep=args.run_num, gen=args.gens, ind="elite")

    #if args.evol_type == 'lexicase':
    evol_utils.Logging.writeLexicaseOrdering(lex_log_file)

    # Write out the last generation to a file.
    evol_utils.Logging.writePopulationInformation(pop_log_file, pop)
    for i in range(len(pop)):
        print(pop[i]._id, pop[i].fitness.values, pop[i].grammar)
        pop[i].image.save("{}/{}/{}/img-{}.png".format(args.output_path,args.treatment,args.run_num,pop[i]._id))
