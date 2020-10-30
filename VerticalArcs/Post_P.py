'''
Sine archetype - post-processing script

Extracts the displacement at the upper midpoint and the maximum stress in the part 

Files needed: jobname+'.odb' - The job file you want to run. 
              
Hardcoded Lines:
    Line 27: the step is hardcoded to 'Analysis' - that could be modified 
             to be specified by the user (via a dictionary of relevant model
             information)
    Line 32, 33: The set names are hardcoded to correspond to the 'Sine_Analysis.py' 
                 script.    
    
'''

from abaqus import *
from abaqusConstants import *
import visualization
import math 
import numpy as np 


def odbPostProcess(jobName,loadFlag):
    ### Obtain Rotation Array 
    odbName = jobName+'.odb'
    odb = visualization.openOdb(odbName)
    step=odb.steps['Step-1']

    ## Call for RP-2 Node Set 
    nodeSet = odb.rootAssembly.nodeSets['TOP_RP']
    elsetName = 'ALL_PART'
    elset = elemset = None 
    region = 'over the entire model'
    assembly = odb.rootAssembly 

    i=0
    frame = step.frames[-1] # we only care about the last frame (snapshot) of data
    forceField = frame.fieldOutputs['RF'] # RF = reaction force 
    forceField_nodeSet = forceField.getSubset(region=nodeSet)
    dispField = frame.fieldOutputs['U'] # U = displacement 
    dispField_nodeSet = dispField.getSubset(region=nodeSet)
    if loadFlag == 1: #x-displacement
        performanceMetric = forceField_nodeSet.values[0].data[0]/dispField_nodeSet.values[0].data[0]
    elif loadFlag == 2: #y-displacement 
        performanceMetric = forceField_nodeSet.values[0].data[1]/dispField_nodeSet.values[0].data[1]
    elif loadFlag == 3: #z-rotation
        momentField = frame.fieldOutputs['RM']
        momentField_nodeSet = momentField.getSubset(region=nodeSet)
        rotationField = frame.fieldOutputs['UR']
        rotationField_nodeSet = rotationField.getSubset(region=nodeSet)
        performanceMetric = momentField_nodeSet.values[0].data[2]/rotationField_nodeSet.values[0].data[2]
        print(rotationField_nodeSet.values[0].data[2],momentField_nodeSet.values[0].data[2])


    ## Scan the entire part for max Strain and Stress 
    if elsetName:
        try:
            elemset = assembly.elementSets[elsetName]
            region = " in the element set : " + elsetName;
        except KeyError:
            print 'An assembly level elset named %s does' \
                   'not exist in the output database %s' \
                   % (elsetName, odbName)
            odb.close()
            exit(0)
                
    """ Initialize maximum values """
    maxMises = -0.1
    maxVMElem = 0



    Stress = 'S'
    allFields = frame.fieldOutputs 
    if (allFields.has_key(Stress)):
        isStressPresent = 1 
        stressSet = allFields[Stress]
        if elemset:
            stressSet = stressSet.getSubset(region=elemset)
        bulkData = stressSet.bulkDataBlocks
        maxMises = max(bulkData[0].mises)

        

    
    odb.close()
    
    return performanceMetric,maxMises 
    
