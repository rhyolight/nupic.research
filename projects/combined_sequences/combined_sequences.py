# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2016, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero Public License for more details.
#
# You should have received a copy of the GNU Affero Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

"""
This file runs a combined HTM network that includes the sensorimotor layers from
the Layers and Columns paper as well as a pure sequence layer.
"""

import os
import numpy
import time
import cPickle
from multiprocessing import Pool, cpu_count
import matplotlib.pyplot as plt
import random

import matplotlib as mpl
mpl.rcParams['pdf.fonttype'] = 42
from matplotlib import rc
rc('font',**{'family':'sans-serif','sans-serif':['Arial']})

from htmresearch.frameworks.layers.combined_sequence_experiment import (
  L4TMExperiment
)
from htmresearch.frameworks.layers.object_machine_factory import (
  createObjectMachine
)


def printDiagnostics(sequences, objects, verbosity=0):
  """Useful diagnostics for debugging."""
  r = sequences.objectConfusion()
  print "Average common pairs in sequences=", r[0],
  print ", features=",r[2]

  r = objects.objectConfusion()
  print "Average common pairs in objects=", r[0],
  print ", locations=",r[1],
  print ", features=",r[2]

  print "Total number of objects created:",len(objects.getObjects())
  print "Total number of sequences created:",len(sequences.getObjects())

  # For detailed debugging
  if verbosity > 0:
    print "Objects are:"
    for o in objects:
      pairs = objects[o]
      pairs.sort()
      print str(o) + ": " + str(pairs)
    print "Sequences:"
    for i in sequences:
      print i,sequences[i]


def trainSequences(sequences, exp):
  """Train the network on all the sequences"""
  print "Training sequences"
  for seqName in sequences:

    # Make sure we learn enough times to deal with high order sequences and
    # remove extra predictions.
    iterations = 3*len(sequences[seqName])
    for p in range(iterations):

      # Ensure we generate new random location for each sequence presentation
      objectSDRs = sequences.provideObjectsToLearn([seqName])
      exp.learnObjects(objectSDRs, reset=False)

      # TM needs reset between sequences, but not other regions
      exp.TMColumns[0].reset()

    # L2 needs resets when we switch to new object
    exp.sendReset()


def trainObjects(objects, exp, numRepeatsPerObject, experimentIdOffset):
  """
  Train the network on all the objects by randomly traversing points on
  each object.  We offset the id of each object to avoid confusion with
  any sequences that might have been learned.
  """
  print "Training objects"

  # We want to traverse the features of each object randomly a few times before
  # moving on to the next object. Create the SDRs that we need for this.
  objectsToLearn = objects.provideObjectsToLearn()
  objectTraversals = {}
  for objectId in objectsToLearn:
    objectTraversals[objectId + experimentIdOffset] = objects.randomTraversal(
      objectsToLearn[objectId], numRepeatsPerObject)

  # Train the network on all the SDRs for all the objects
  exp.learnObjects(objectTraversals)


def inferSequence(exp, sequenceId, sequences):
  """Run inference on the given sequence."""
  assert exp.numColumns == 1

  sequence = sequences[sequenceId]

  # Create sequence of sensations for this sequence for one column.
  objectSensations = {}
  objectSensations[0] = []
  objectCopy = [pair for pair in sequence]
  for pair in objectCopy:
    objectSensations[0].append(pair)

  inferConfig = {
    "numSteps": len(objectSensations[0]),
    "pairs": objectSensations,
  }

  inferenceSDRs = sequences.provideObjectToInfer(inferConfig)

  exp.infer(inferenceSDRs, objectName=sequenceId)


def inferObject(exp, objectId, objects, objectName):
  """
  Run inference on the given object.
  objectName is the name of this object in the experiment.
  """
  assert exp.numColumns == 1

  # Create sequence of random sensations for this object for one column. The
  # total number of sensations is equal to the number of points on the object.
  # No point should be visited more than once.
  objectSensations = {}
  objectSensations[0] = []
  obj = objects[objectId]
  objectCopy = [pair for pair in obj]
  random.shuffle(objectCopy)
  for pair in objectCopy:
    objectSensations[0].append(pair)

  inferConfig = {
    "numSteps": len(objectSensations[0]),
    "pairs": objectSensations,
    "includeRandomLocation": False,
  }

  inferenceSDRs = objects.provideObjectToInfer(inferConfig)

  exp.infer(inferenceSDRs, objectName=objectName)


def runExperiment(args):
  """
  Runs the experiment.  What did you think this does?

  args is a dict representing the various parameters. We do it this way to
  support multiprocessing. args contains one or more of the following keys:

  The function returns the args dict updated with a number of additional keys
  containing performance metrics.
  """
  numObjects = args.get("numObjects", 10)
  numSequences = args.get("numSequences", 10)
  numFeatures = args.get("numFeatures", 10)
  seqLength = args.get("seqLength", 10)
  numPoints = args.get("numPoints", 10)
  trialNum = args.get("trialNum", 42)
  plotInferenceStats = args.get("plotInferenceStats", True)
  inputSize = args.get("inputSize", 512)
  numLocations = args.get("numLocations", 100000)
  numInputBits = args.get("inputBits", 20)
  settlingTime = args.get("settlingTime", 3)
  numColumns = 1

  random.seed(trialNum)

  #####################################################
  #
  # Create the sequences and objects, and make sure they share the
  # same features and locations.

  sequences = createObjectMachine(
    machineType="sequence",
    numInputBits=numInputBits,
    sensorInputSize=inputSize,
    externalInputSize=1024,
    numCorticalColumns=numColumns,
    numFeatures=numFeatures,
    seed=trialNum
  )

  objects = createObjectMachine(
    machineType="simple",
    numInputBits=numInputBits,
    sensorInputSize=inputSize,
    externalInputSize=1024,
    numCorticalColumns=numColumns,
    numFeatures=numFeatures,
    seed=trialNum
  )

  # Make sure they share the same features and locations
  objects.locations = sequences.locations
  objects.features = sequences.features

  sequences.createRandomSequences(numSequences, seqLength)
  objects.createRandomObjects(numObjects, numPoints=numPoints,
                                    numLocations=numLocations,
                                    numFeatures=numFeatures)

  printDiagnostics(sequences, objects)

  #####################################################
  #
  # Setup experiment and train the network
  name = "combined_sequences_S%03d_O%03d_F%03d_L%03d_T%03d" % (
    numSequences, numObjects, numFeatures, numLocations, trialNum
  )
  exp = L4TMExperiment(
    name=name,
    numCorticalColumns=numColumns,
    inputSize=inputSize,
    numExternalInputBits=numInputBits,
    externalInputSize=1024,
    numInputBits=numInputBits,
    seed=trialNum,
    L4Overrides={"initialPermanence": 0.41,
                 "activationThreshold": 18,
                 "minThreshold": 18,
                 "basalPredictedSegmentDecrement": 0.0001},
  )

  # Train the network on all the sequences and then all the objects.
  trainSequences(sequences, exp)
  trainObjects(objects, exp, settlingTime, numSequences)

  #####################################################
  #
  # For inference, we will randomly pick an object or a sequence and
  # check and plot convergence for each item.

  for trial,itemType in enumerate(["sequence", "object", "sequence", "object",
                                   "sequence", "sequence", "object", "sequence", ]):
    # itemType = ["sequence", "object"][random.randint(0, 1)]
    # itemType = "sequence"

    if itemType == "sequence":
      objectId = random.randint(0, numSequences-1)
      inferSequence(exp, objectId, sequences)

    else:
      objectId = random.randint(0, numObjects-1)
      inferObject(exp, objectId, objects, objectId+numSequences)

    if plotInferenceStats:
      plotOneInferenceRun(
        exp.statistics[trial],
        fields=[
          # ("L4 Predicted", "Predicted sensorimotor cells"),
          # ("L2 Representation", "L2 Representation"),
          # ("L4 Representation", "Active sensorimotor cells"),
          ("L4 PredictedActive", "Predicted active cells in sensorimotor layer"),
          ("TM NextPredicted", "Predicted cells in temporal sequence layer"),
          ("TM PredictedActive", "Predicted active cells in temporal sequence layer"),
        ],
        basename=exp.name,
        itemType=itemType,
        experimentID=trial,
        plotDir=os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             "detailed_plots")
      )

  # Compute overall inference statistics
  infStats = exp.getInferenceStats()
  convergencePoint, accuracy = exp.averageConvergencePoint(
    "L2 Representation", 30, 40, 1)

  predictedActive = numpy.zeros(len(infStats))
  predicted = numpy.zeros(len(infStats))
  predictedActiveL4 = numpy.zeros(len(infStats))
  predictedL4 = numpy.zeros(len(infStats))
  for i,stat in enumerate(infStats):
    predictedActive[i] = float(sum(stat["TM PredictedActive C0"][2:])) / len(stat["TM PredictedActive C0"][2:])
    predicted[i] = float(sum(stat["TM NextPredicted C0"][2:])) / len(stat["TM NextPredicted C0"][2:])

    predictedActiveL4[i] = float(sum(stat["L4 PredictedActive C0"])) / len(stat["L4 PredictedActive C0"])
    predictedL4[i] = float(sum(stat["L4 Predicted C0"])) / len(stat["L4 Predicted C0"])

  print "# Sequences {} # features {} trial # {}".format(
    numSequences, numFeatures, trialNum)
  print "Average convergence point=",convergencePoint,
  print "Accuracy:", accuracy
  print

  # Return our convergence point as well as all the parameters and objects
  args.update({"objects": sequences.getObjects()})
  args.update({"convergencePoint":convergencePoint})
  args.update({"sensorimotorAccuracyPct": accuracy})
  args.update({"averagePredictions": predicted.mean()})
  args.update({"averagePredictedActive": predictedActive.mean()})
  args.update({"averagePredictionsL4": predictedL4.mean()})
  args.update({"averagePredictedActiveL4": predictedActiveL4.mean()})
  args.update({"name": exp.name})
  args.update({"statistics": exp.statistics})

  # Can't pickle experiment so can't return it for batch multiprocessing runs.
  # However this is very useful for debugging when running in a single thread.
  # if plotInferenceStats:
  #   args.update({"experiment": exp})
  return args


def runExperimentPool(numSequences,
                      numFeatures,
                      numLocations,
                      numWorkers=7,
                      nTrials=1,
                      seqLength=10,
                      resultsName="convergence_results.pkl"):
  """
  Allows you to run a number of experiments using multiple processes.
  For each parameter except numWorkers, pass in a list containing valid values
  for that parameter. The cross product of everything is run, and each
  combination is run nTrials times.

  Returns a list of dict containing detailed results from each experiment.
  Also pickles and saves the results in resultsName for later analysis.

  Example:
    results = runExperimentPool(
                          numSequences=[10],
                          numFeatures=[5],
                          numWorkers=8,
                          nTrials=5)
  """
  # Create function arguments for every possibility
  args = []

  for o in reversed(numSequences):
    for l in numLocations:
      for f in numFeatures:
        for t in range(nTrials):
          args.append(
            {"numSequences": o,
             "numFeatures": f,
             "trialNum": t,
             "seqLength": seqLength,
             "numLocations": l,
             "plotInferenceStats": False,
             }
          )
  print "{} experiments to run, {} workers".format(len(args), numWorkers)
  # Run the pool
  if numWorkers > 1:
    pool = Pool(processes=numWorkers)
    result = pool.map(runExperiment, args)
  else:
    result = []
    for arg in args:
      result.append(runExperiment(arg))

  # Pickle results for later use
  with open(resultsName,"wb") as f:
    cPickle.dump(result,f)

  return result


def plotOneInferenceRun(stats,
                       fields,
                       basename,
                       itemType="",
                       plotDir="plots",
                       experimentID=0):
  """
  Plots individual inference runs.
  """
  if not os.path.exists(plotDir):
    os.makedirs(plotDir)

  plt.figure()
  objectName = stats["object"]

  # plot request stats
  for field in fields:
    fieldKey = field[0] + " C0"
    plt.plot(stats[fieldKey], marker='+', label=field[1])

  # format
  plt.legend(loc="upper right")
  plt.xlabel("Input number")
  plt.xticks(range(stats["numSteps"]))
  plt.ylabel("Number of cells")
  plt.ylim(-5, 100)
  # plt.ylim(plt.ylim()[0] - 5, plt.ylim()[1] + 5)
  plt.title("Activity while inferring {}".format(itemType))

  # save
  relPath = "{}_exp_{}.pdf".format(basename, experimentID)
  path = os.path.join(plotDir, relPath)
  plt.savefig(path)
  plt.close()


if __name__ == "__main__":

  startTime = time.time()
  dirName = os.path.dirname(os.path.realpath(__file__))

  # This runs the first experiment in the section "Simulations with Pure
  # Temporal Sequences"
  if False:
    resultsFilename = os.path.join(dirName, "pure_sequences_example.pkl")
    results = runExperiment(
                  {
                    "numSequences": 5,
                    "seqLength": 10,
                    "numFeatures": 10,
                    "trialNum": 4,
                    "numObjects": 0,
                    "numLocations": 100,
                    "plotInferenceStats": True,  # Outputs detailed graphs
                  }
              )

    # Pickle results for plotting and possible later debugging
    with open(resultsFilename, "wb") as f:
      cPickle.dump(results, f)


  # This runs the experiment the section "Simulations with Combined Sequences"
  if True:
    resultsFilename = os.path.join(dirName, "combined_results.pkl")
    results = runExperiment(
                  {
                    "numSequences": 50,
                    "seqLength": 10,
                    "numObjects": 50,
                    "numFeatures": 50,
                    "trialNum": 8,
                    "numLocations": 50,
                    "plotInferenceStats": True,  # Outputs detailed graphs
                    "settlingTime": 3,
                  }
              )

    # Pickle results for plotting and possible later debugging
    with open(resultsFilename, "wb") as f:
      cPickle.dump(results,f)

  print "Actual runtime=",time.time() - startTime
