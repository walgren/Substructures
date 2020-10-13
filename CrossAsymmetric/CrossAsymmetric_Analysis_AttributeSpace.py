'''
Substructure script - Asymmetric geometry 

Modifies the asymmetric lattice archetype to create a substructure with different 
design variables (currently thick13, thick24 and inner fillet)

Files needed: CrossAsymmetric.cae - .cae with the circle created	***DO NOT OVERWRITE
			  WITH JOB DATA***
			  Abaqus version 2018
			  
Hardcoded Lines:
	Throughout: The model name and part names are hardcoded. Consider changing
	variable "model" to a dictionary that contains all relevant model information
	(e.g., model['partName'] = 'CrossAsymmetric', etc.)

Bounds:
	Denoted near call of functions
	
'''
from abaqus import *
from abaqusConstants import *
from caeModules import *

from math import *
import time
import numpy as np
import os 
import csv
import fileinput #needed for input file modification

from Post_P import * 

start = time.time()

session.journalOptions.setValues(replayGeometry=COORDINATE,recoverGeometry=COORDINATE)

## INITIALIZE VARIABLES
thickness = 1.5
fillet = 0.5

DSeed=0.5 #seedSize
stiffenerSeed=.5 #seedSize
globalSeed=.5 #seedSize

dim = [-0.005, -0.005, 0.0, 0.005, 0.005, 0.0] #[minX,minY,minZ,maxX,maxY,maxZ]

model='CrossAsymmetric.cae'
openMdb(model)

def changeMaterial(section, material):
	"""
	Change material of given section to preconstructed material
	
	"""
	
	# mdb.models['Model-1'].materials['stiffMaterial'].elastic.setValues(table=((
	# newEValue, 0.33), ))
	mdb.models['Model-1'].sections[section].setValues(preIntegrate=OFF, 
	material=material, thicknessType=UNIFORM, thickness=1.0, 
	thicknessField='', nodalThicknessField='', idealization=NO_IDEALIZATION, 
	integrationRule=SIMPSON, numIntPts=5)
	return


def modifyDimensions(width=(dim[3]-dim[0]),height=(dim[4]-dim[1]),depth=0):
	"""Modify substructure dimensions with function taking in dimensions defined by dim list by default
	
	Arguments:
		width: Substructure width (convert to meters for continuity of units)
		height: Substructure width (convert to meters for continuity of units)
	
	Return: New dimensions of dim centered at 0,0,0
		
	"""
	p = mdb.models['Model-1'].parts['Cross']
	s = p.features['Shell planar-1'].sketch
	mdb.models['Model-1'].ConstrainedSketch(name='__edit__', objectToCopy=s)
	s1 = mdb.models['Model-1'].sketches['__edit__']
	g, v, d, c = s1.geometry, s1.vertices, s1.dimensions, s1.constraints
	s1.setPrimaryObject(option=SUPERIMPOSE)
	p.projectReferencesOntoSketch(sketch=s1, 
		upToFeature=p.features['Shell planar-1'], filter=COPLANAR_EDGES)
		
	s=mdb.models['Model-1'].sketches['__edit__']
	s.parameters['SubWidth'].setValues(expression=str(width))
	s.parameters['SubHeight'].setValues(expression=str(height))
	
	p = mdb.models['Model-1'].parts['Cross']
	p.features['Shell planar-1'].setValues(sketch=s1)
	
	p.regenerate()
	
	return [-width/2, -height/2, -depth/2, width/2, height/2, depth/2]


def modifyCross(model,cornerSize,thick13,thick24,fillet):
	"""Modify Design Variables (DVs)
	
	##	IMPORTANT: Thickness of cross members (bL), Corner edge size (aL), Substructure width (L)
	##	Range of a: {0<a<0.5}
	##	Range of b: {0<b<sqrt(2)*a}	(For meshing purposes max b ~ a and min > 0)
	##	Range of fillet: unknown
	
	Arguments:
		model: Abaqus model in which to create the part
		cornerSize: Percentage used to define the corner edge size (should NOT be changed during substructure generation to maintain corner interface)
		thick13 & thick24: Percentages used to define thicknesses of cross members in quadrants 1/3 or 2/4
		fillet: Percentage used to define inner fillets of substructure
		
		Note: The percentage values are used relative to the substructure's width and has only been tested with square substructures
	
	"""

	p = mdb.models['Model-1'].parts['Cross']
	s = p.features['Partition face-1'].sketch
	mdb.models['Model-1'].ConstrainedSketch(name='__edit__', objectToCopy=s)
	s1 = mdb.models['Model-1'].sketches['__edit__']
	g, v, d, c = s1.geometry, s1.vertices, s1.dimensions, s1.constraints
	s1.setPrimaryObject(option=SUPERIMPOSE)
	p.projectReferencesOntoSketch(sketch=s1, 
		upToFeature=p.features['Partition face-1'], filter=COPLANAR_EDGES)
	
	s=mdb.models['Model-1'].sketches['__edit__']
	s.parameters['CornerEdge'].setValues(expression=str(cornerSize)+'*SubWidth')
	s.parameters['fillet'].setValues(expression=str(fillet)+'*SubWidth')
	s.parameters['Thick13'].setValues(expression=str(thick13)+'*SubWidth')
	s.parameters['Thick24'].setValues(expression=str(thick24)+'*SubWidth')
	
	p = mdb.models['Model-1'].parts['Cross']
	p.features['Partition face-1'].setValues(sketch=s1)
	
	p.regenerate()
		
	return part 


def meshCross(model,globalSeed):
	"""Mesh the substructure part.
	 
	 Arguments:
		Model:Abaqus model in which to mesh the part
		seedSize: local seed size 
		
	"""	   
	p = mdb.models['Model-1'].parts['Cross']

	p.deleteMesh()
	
	# Mesh Part
	p.seedPart(size=globalSeed, deviationFactor=0.1, minSizeFactor=0.1)
	p.generateMesh()
	return part 
	
	
def retainBCs(modelData,dim):
	'''
	Create boundary conditions to specify retained DOFs on the part. 
	
	Parameters
	----------
	modelData : DICTIONARY
		modelData = {
			'modelName':modelName,
			'partName':partName,
			'stepName':stepName,
			'retained_Nodes':retained_Nodes,
			'retained_DOFs':retained_DOFs,
			'modelName_Sub':'Substructure_Model
			'stepName_Sub':'subGenerate'
			'dim',dim}
			(As of 7/14/2020)
	dim : LIST
		Overall dimensions of the part [minX,minY,minZ,maxX,maxY,maxZ]

	Returns
	-------
	part : placeholder
		nothing currently. Could omit or pass back relevant information. Future
		development would include error handling.
	'''
	modelName = modelData['modelName_Sub']
	stepName = modelData['stepName_Sub']
	partName = modelData['partName']
	instanceName = partName+'-1'
	# Top Face
	a = mdb.models[modelName].rootAssembly
	e1 = a.instances[instanceName].edges
	edges1 = e1.getByBoundingBox(dim[0],0.99*dim[4],dim[2],dim[3],1.01*dim[4],dim[5])
	a.Set(edges=edges1, name='Top')

	# Bottom Face
	a = mdb.models[modelName].rootAssembly
	e1 = a.instances[instanceName].edges
	edges1 = e1.getByBoundingBox(dim[0],1.01*dim[1],dim[2],dim[3],.99*dim[1],dim[5])
	a.Set(edges=edges1, name='Bottom')
	
	#Left Face 
	a = mdb.models[modelName].rootAssembly
	e1 = a.instances[instanceName].edges
	edges1 = e1.getByBoundingBox(1.01*dim[0],dim[1],dim[2],.99*dim[0],dim[4],dim[5])
	a.Set(edges=edges1, name='Left')
	
	#Right Face
	a = mdb.models[modelName].rootAssembly
	e1 = a.instances[instanceName].edges
	edges1 = e1.getByBoundingBox(.99*dim[3],dim[1],dim[2],1.01*dim[3],dim[4],dim[5])
	a.Set(edges=edges1, name='Right')
	
	# Specify Retained Nodal BCs
	a = mdb.models[modelName].rootAssembly
	region = a.sets['Bottom']
	mdb.models[modelName].RetainedNodalDofsBC(name='BottomFix', createStepName=stepName, 
		region=region, u1=ON, u2=ON, u3=ON, ur1=ON, ur2=ON, ur3=ON)

	a = mdb.models[modelName].rootAssembly
	region = a.sets['Top']
	mdb.models[modelName].RetainedNodalDofsBC(name='TopFix', createStepName=stepName, 
		region=region, u1=ON, u2=ON, u3=ON, ur1=ON, ur2=ON, ur3=ON)	   
		
	a = mdb.models[modelName].rootAssembly
	region = a.sets['Left']
	mdb.models[modelName].RetainedNodalDofsBC(name='LeftFix', createStepName=stepName, 
		region=region, u1=ON, u2=ON, u3=ON, ur1=ON, ur2=ON, ur3=ON)

	a = mdb.models[modelName].rootAssembly
	region = a.sets['Right']
	mdb.models[modelName].RetainedNodalDofsBC(name='RightFix', createStepName=stepName, 
		region=region, u1=ON, u2=ON, u3=ON, ur1=ON, ur2=ON, ur3=ON)	   
	
	
	return part 


def modifySub(modelData,i):
	'''
	Modify substructure identifier to create unique substructure for the 
	current configuration. 
	
	Parameters
	----------
	modelData : DICTIONARY
		modelData = {
			'modelName':modelName,
			'partName':partName,
			'stepName':stepName,
			'retained_Nodes':retained_Nodes,
			'retained_DOFs':retained_DOFs,
			'modelName_Sub':'Substructure_Model'
			'stepName_Sub':'subGenerate'
			'dim',dim}
			(As of 7/14/2020)
	i : INT
		Substructure identifier (can be 1-9999)

	Returns
	-------
	part : placeholder
		nothing currently. Could omit or pass back relevant information. Future
		development would include error handling.
	'''
	modelName = modelData['modelName_Sub']
	stepName = modelData['stepName_Sub']
	mdb.models[modelName].steps[stepName].setValues(substructureIdentifier=i)
	print('Sub ID: '+str(i))

	return part 
	
	
def runModel(model,i):
	'''
	Run substructure generation job with unique job name (in this case 'Circle-1,
	for example). Waits for completion in this function. 
	
	Parameters
	----------
	model : STR
		Currently the model name (Baseline.cae). Should be updated to a dictionary
		containing all relevant model info to eliminate all the hardcoded
		part and model calls.
	i : INT
		Substructure identifier (can be 1-9999)

	Returns
	-------
	part : placeholder
		nothing currently. Could omit or pass back relevant information. Future
		development would include error handling.
	'''
	
	# Create Job
	jobName='Cross-'+str(i)
	job= mdb.Job(name=jobName, model='Model-1', description='', type=ANALYSIS, 
		atTime=None, waitMinutes=0, waitHours=0, queue=None, memory=90, 
		memoryUnits=PERCENTAGE, getMemoryFromAnalysis=True, 
		explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE, echoPrint=OFF, 
		modelPrint=OFF, contactPrint=OFF, historyPrint=OFF, userSubroutine='', 
		scratch='', resultsFormat=ODB, multiprocessingMode=DEFAULT, numCpus=1, 
		numGPUs=0)
	
	#Run Job
	job.submit(consistencyChecking=OFF)
	job.waitForCompletion()
	return jobName


def takeScreenshot(model,innerR,thickness):
	'''
	Save a .png of the current substructure with the mesh on to the /screenshots
	folder. 
	Parameters
	----------
	model : STR
		Currently the model name (Baseline.cae). Should be updated to a dictionary
		containing all relevant model info to eliminate all the hardcoded
		part and model calls.
	innerR : FLOAT
		Design variable to describe the inner radius of the circle geometry
	thickness : FLOAT
		Design variable to describe the thickness of the stiffening member.

	Returns
	-------
	part : none
		placeholder for now.

	'''
	path = os.getcwd()+'/Pictures/'+str(counter)
	p = mdb.models['Model-1'].parts['Cross']
	session.viewports['Viewport: 1'].setValues(displayedObject=p)
	session.viewports['Viewport: 1'].view.setValues(session.views['Front'])
	session.viewports['Viewport: 1'].partDisplay.setValues(mesh=OFF)
	session.viewports['Viewport: 1'].partDisplay.meshOptions.setValues(
		meshTechnique=ON)
	session.viewports['Viewport: 1'].partDisplay.geometryOptions.setValues(
		referenceRepresentation=OFF)
	session.viewports['Viewport: 1'].enableMultipleColors()
	# session.viewports['Viewport: 1'].setColor(initialColor='#BDBDBD')
	cmap=session.viewports['Viewport: 1'].colorMappings['Section']
	session.viewports['Viewport: 1'].setColor(colorMapping=cmap)
	session.viewports['Viewport: 1'].disableMultipleColors()
	session.viewports['Viewport: 1'].partDisplay.setValues(renderStyle=SHADED)
	#Print 1 png without mesh
	session.pngOptions.setValues(imageSize=(1000, 407))
	session.printToFile(
		fileName=(path+'.png'), 
		format=PNG, canvasObjects=(session.viewports['Viewport: 1'], )) 
	return part 


def createAnalyticalSurface(model,dim):
	'''
	Creates an analytical rigid surface to easily apply boundary conditions 
	
	Parameters
	----------
	model : STR
		Currently the model name (Baseline.cae). Should be updated to a dictionary
		containing all relevant model info to eliminate all the hardcoded
		part and model calls.
	dim : LIST
		Overall model geometric parameters 
		dim = [minX,minY,minZ,maxX,maxY,maxZ]

	Returns
	-------
	None
	'''
	minX = dim[0]
	maxX = dim[3]
	s1 = mdb.models['Model-1'].ConstrainedSketch(name='__profile__', 
		sheetSize=200.0)
	g, v, d, c = s1.geometry, s1.vertices, s1.dimensions, s1.constraints
	s1.setPrimaryObject(option=STANDALONE)
	s1.Line(point1=(minX*1.5, 0.0), point2=(maxX*1.5, 0.0))
	p = mdb.models['Model-1'].Part(name='Surface', dimensionality=THREE_D, 
		type=ANALYTIC_RIGID_SURFACE)
	p = mdb.models['Model-1'].parts['Surface']
	p.AnalyticRigidSurfExtrude(sketch=s1, depth=10.0)
	s1.unsetPrimaryObject()
	p = mdb.models['Model-1'].parts['Surface']
	
	return 


def instanceAnalyticalSurface(model,dim):
	'''
	Places the Analytical rigid surface in the assembly, currently at the top (in the y-dimension)
	of the part.
	
	ALL OF THE GEOMETRY IS ASSUMING THAT THE PART IS CENTERED AT (0,0,0).
	
	Parameters
	----------
	model : STR
		Currently the model name (Baseline.cae). Should be updated to a dictionary
		containing all relevant model info to eliminate all the hardcoded
		part and model calls.
	dim : LIST
		Overall model geometric parameters 
		dim = [minX,minY,minZ,maxX,maxY,maxZ]

	Returns
	-------
	None	
	'''
	yMax = dim[4]
	# Instance Part 
	a1 = mdb.models['Model-1'].rootAssembly
	p = mdb.models['Model-1'].parts['Surface']
	a1.Instance(name='Surface-1', part=p, dependent=ON)

	# Move surface to top (in y-dimension) of the part
	a1 = mdb.models['Model-1'].rootAssembly
	a1.translate(instanceList=('Surface-1', ), vector=(0.0, yMax, 0.0))
	
	
	return 


def defineRigidBody(model,dim):
	'''
	Creates a rigid body definition for the analytical rigid surface based on a 
	reference point (defined in this function as well).
	
	ALL OF THE GEOMETRY IS ASSUMING THAT THE PART IS CENTERED AT (0,0,0).
	
	NEED TO CHECK IF THE REFERENCE POINT INDEX (Currently hardcoded at r1[10]) CHANGES.
	THIS IS ACCOMPLISHED PASSIVELY BY THE PRINT STATEMENT 
	Parameters
	----------
	model : STR
		Currently the model name (Baseline.cae). Should be updated to a dictionary
		containing all relevant model info to eliminate all the hardcoded
		part and model calls.
	dim : LIST
		Overall model geometric parameters 
		dim = [minX,minY,minZ,maxX,maxY,maxZ]

	Returns
	-------
	None	
	'''
	yMax = dim[4]
	
	#Create reference point 
	a = mdb.models['Model-1'].rootAssembly
	a.ReferencePoint(point=(0.0, yMax, 0.0))
	
	#Create rigid body definition
	a = mdb.models['Model-1'].rootAssembly
	s1 = a.instances['Surface-1'].faces
	side2Faces1 = s1.findAt(((0.0, yMax, -1.0), ))
	region5=a.Surface(side2Faces=side2Faces1, name='RigidBody')
	a = mdb.models['Model-1'].rootAssembly
	r1 = a.referencePoints
	print(r1.keys()[0])
	refPoints1=(r1[r1.keys()[0]], ) # This convoluted line of code ensures to grab the first
	#reference point, no matter the key. If there are multiple reference points in the model,
	#this may fail. 
	region1=regionToolset.Region(referencePoints=refPoints1)
	mdb.models['Model-1'].RigidBody(name='RigidBody', refPointRegion=region1, 
		surfaceRegion=region5)
	
	return 


def tieBody_and_Part(model,dim):
	'''
	Ties the analytical rigid body to the analysis part.
	
	ALL OF THE GEOMETRY IS ASSUMING THAT THE PART IS CENTERED AT (0,0,0).
	
	Parameters
	----------
	model : STR
		Currently the model name (Baseline.cae). Should be updated to a dictionary
		containing all relevant model info to eliminate all the hardcoded
		part and model calls.
	dim : LIST
		Overall model geometric parameters 
		dim = [minX,minY,minZ,maxX,maxY,maxZ]

	Returns
	-------
	None	
	'''
	minX = dim[0]
	minY = dim[1]
	maxX = dim[3]
	maxY = dim[4]
	a = mdb.models['Model-1'].rootAssembly
	region1=a.surfaces['RigidBody']
	a = mdb.models['Model-1'].rootAssembly
	e1 = a.instances['Cross-1'].edges
	edges1 = e1.getByBoundingBox(1.5*minX,0.95*maxY, -1.0,1.5*maxX,1.05*maxY,1.0)
	region2=a.Set(edges=edges1, name='Top_Edge')
	mdb.models['Model-1'].Tie(name='Tie', master=region1, slave=region2, 
		positionToleranceMethod=COMPUTED, adjust=ON, tieRotations=ON, 
		thickness=OFF)

	return 


def modifyStep(model):
	'''Deletes the substructureGenerate step 
	and creates a Static,General step'''
	#Try to delete step 1 (assuming it is a substructure generate step)
	try:
		del mdb.models['Model-1'].steps['Step-1']
	except:
		print('Step-1 Does not exist')
		
	#Create a static, general step 
	mdb.models['Model-1'].StaticStep(name='Step-1', previous='Initial')
	return 


def encastreBottom(model,dim):
	'''Creates an encastre (fixed) boundary condition 
	on the bottom edge of the part
		
	ALL OF THE GEOMETRY IS ASSUMING THAT THE PART IS CENTERED AT (0,0,0).
	
	Parameters
	----------
	model : STR
		Currently the model name (Baseline.cae). Should be updated to a dictionary
		containing all relevant model info to eliminate all the hardcoded
		part and model calls.
	dim : LIST
		Overall model geometric parameters 
		dim = [minX,minY,minZ,maxX,maxY,maxZ]
	'''
	minX = dim[0]
	maxX = dim[3]
	minY = dim[1]
	a1 = mdb.models['Model-1'].rootAssembly
	e1 = a1.instances['Cross-1'].edges
	edges1 = e1.getByBoundingBox(1.5*minX,1.05*minY, -1.0,1.5*maxX,0.95*minY,1.0)
	region = a1.Set(edges=edges1, name='Set-3')
	mdb.models['Model-1'].EncastreBC(name='FIX_BOTTOM', createStepName='Initial', 
		region=region, localCsys=None)
	
	return 


def xDisplacement(model,disp,subWidth):
	'''Creates a displacement at the top reference point
	   Uses disp * subWidth to get a normalized displacement
	'''
	
	a1 = mdb.models['Model-1'].rootAssembly
	r1 = a1.referencePoints
	refPoints1=(r1[r1.keys()[0]], )
	region = a1.Set(referencePoints=refPoints1, name='TOP_RP')
	mdb.models['Model-1'].DisplacementBC(name='MOVE_RP', createStepName='Step-1', 
		region=region, u1=disp*subWidth, u2=0.0, u3=UNSET, ur1=UNSET, ur2=UNSET, ur3=0.0, 
		amplitude=UNSET, fixed=OFF, distributionType=UNIFORM, fieldName='', 
		localCsys=None)
		
	return 


def createJob(model,jobName):
	''' Creates a job to correspond to the x-displacement load case'''
	mdb.Job(name=jobName, model='Model-1', description='', type=ANALYSIS, 
		atTime=None, waitMinutes=0, waitHours=0, queue=None, memory=90, 
		memoryUnits=PERCENTAGE, getMemoryFromAnalysis=True, 
		explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE, echoPrint=OFF, 
		modelPrint=OFF, contactPrint=OFF, historyPrint=OFF, userSubroutine='', 
		scratch='', resultsFormat=ODB, multiprocessingMode=DEFAULT, numCpus=1, 
		numGPUs=0)
	return jobName


def analysisStep(model,dim,theta,thickness):
	'''
	Revises the model to run a static general analysis step instead of a substructure generation one.
	Creates an encastre boundary condition on the bottom surface and a edge load on the top stiffener surface
	at a prescribed angle (theta)
	----------
	model : STR
		Currently the model name (Baseline.cae). Should be updated to a dictionary
		containing all relevant model info to eliminate all the hardcoded
		part and model calls.
	dim : LIST
		Overall model geometric parameters 
		dim = [minX,minY,minZ,maxX,maxY,maxZ]
	theta : FLT
		The angle at which the shell edge load is oriented. For use as a parameter in P3GA.
	thickness : FLT 
		Thickness of the stiffening section (design variable)

	Returns
	-------
	None

	'''
	# delete substructure generation step 
	del mdb.models['Model-1'].steps['Step-1']
	
	#create analysis step (static, general)
	mdb.models['Model-1'].StaticStep(name='Analysis', previous='Initial')
	
	#create boundary conditions 
	
	#encastre bottom
	a = mdb.models['Model-1'].rootAssembly
	e1 = a.instances['Cross-1'].edges
	edges1 = e1.getByBoundingBox(1.1*dim[0],1.1*dim[1],-0.5,1.1*dim[3],0.9*dim[1],0.5)
	region = a.Set(edges=edges1, name='Bottom_Edge')
	mdb.models['Model-1'].EncastreBC(name='Encastre', createStepName='Initial', 
		region=region, localCsys=None)
	
	#force at the top midpoint
	theta_radians = radians(theta)
	xDirection = cos(theta_radians)	   
	yDirection = sin(theta_radians)
	
	forceMagnitude = 1.0E3*thickness #normalize the force 
	a = mdb.models['Model-1'].rootAssembly
	s1 = a.instances['Cross-1'].edges
	side1Edges1 = s1.findAt((((dim[3]+dim[0])/2.0, dim[4], 0.0), ))
	region = a.Surface(side1Edges=side1Edges1, name='Top_Middle')
	mdb.models['Model-1'].ShellEdgeLoad(name='Stiff_Load', 
		createStepName='Analysis', region=region, magnitude=forceMagnitude, 
		directionVector=((0.0, 0.0, 0.0), (xDirection, yDirection, 0.0)), 
		distributionType=UNIFORM, field='', localCsys=None, traction=GENERAL)

	return forceMagnitude
	
	
def postProcessingSets(model,dim):
	'''
	Creates the geometry sets 'TOP_MIDDLE' and 'ALL_PART' for post-processing
	
	Parameters
	----------
	model : STR
		Currently the model name (Baseline.cae). Should be updated to a dictionary
		containing all relevant model info to eliminate all the hardcoded
		part and model calls.
	dim : LIST
		Overall model geometric parameters 
		dim = [minX,minY,minZ,maxX,maxY,maxZ]

	Returns
	-------
	None
	'''
	#Create TOP_MIDDLE geometry set
	a = mdb.models['Model-1'].rootAssembly
	v1 = a.instances['Cross-1'].vertices
	verts1 = v1.findAt(((0.0, dim[4], 0.0), ))
	a.Set(vertices=verts1, name='TOP_MIDDLE')
	
	#Create ALL_PART geometry set
	a = mdb.models['Model-1'].rootAssembly
	f1 = a.instances['Cross-1'].faces
	faces1 = f1.getByBoundingBox(1.1*dim[0],1.1*dim[1],-0.5,1.1*dim[3],1.1*dim[4],0.5)
	a.Set(faces=faces1, name='ALL_PART')
	
	
	return
	
def substructureModel(modelData,i,matricesFile = 'MATRICES'):
	'''
	Creates a new model and performs a linear substructure generation step
	on the instance defined in 'partName'. Input file is then modified to
	output reduced stiffness matrix and substructure transformation matrix
	to a .mtx file. Job is created and ran in parallel to other processes.
	As of yet (5/21/2020), no issue has arisen in terms of computational
	resources, as a single linear substructure case is fast to run.

	Parameters
	----------
	modelData : DICTIONARY
		modelData = {
			'modelName':modelName,
			'partName':partName,
			'stepName':stepName,
			'retained_Nodes':retained_Nodes,
			'retained_DOFs':retained_DOFs,
			'modelName_Sub':'Substructure_Model'
			'dim',dim}
			(As of 7/14/2020)
	matrixFile: STR
		optional parameter for the .mtx file to which Abaqus will write
		the reduced stiffness and transformation matrices.
	i : STR
		Counter to track the current substructure identifier 

	Returns
	-------
	None.

	'''
	# Data Unpackaging
	modelName = modelData['modelName']
	partName = modelData['partName']
	stepName = modelData['stepName']
	jobName = partName+'-'+str(i)

	dim = modelData['dim']
	modelName_Sub = 'Substructure_Model'
	stepName_Sub = 'subGenerate'
	modelData['modelName_Sub'] = modelName_Sub
	modelData['stepName_Sub'] = stepName_Sub
	# Makes a copy of current model and names it 'Substructure_Model'
	mdb.Model(name=modelName_Sub, objectToCopy=mdb.models[modelName])

	# Deletes step 1
	a = mdb.models[modelName_Sub].rootAssembly
	p = mdb.models[modelName_Sub].parts[partName]
	del mdb.models[modelName_Sub].steps[stepName]
	
	# Makes 'subGenerate' step in copied model
	mdb.models[modelName_Sub].SubstructureGenerateStep(name=stepName_Sub,
		previous='Initial', substructureIdentifier=1)
	 
	modifySub(modelData,i)
	a1 = mdb.models[modelName_Sub].rootAssembly
	p = mdb.models[modelName_Sub].parts[partName]
	instanceName = partName+'-1'
	a1.Instance(name=instanceName, part=p, dependent=ON)
	if "retained_Nodes" in modelData:
		retained_Nodes = modelData['retained_Nodes'] # List of nodes on which the DOFs are retained
		retained_DOFs = modelData['retained_DOFs'] # List of Lists DOF that correspond to each retained nodes
		i = 0
		for retained_Node in retained_Nodes:
			a = mdb.models[modelName_Sub].rootAssembly
			v1 = a.instances[instanceName].vertices
			verts1 = v1[retained_Node:retained_Node+1]
			BC_name = 'NODE_'+str(retained_Node)
			region = a.Set(vertices=verts1,name=BC_name)
			U = [OFF,OFF,OFF,OFF,OFF,OFF]
			for retained_DOF in retained_DOFs[i]:
				U[retained_DOF] = ON
			mdb.models[modelName_Sub].RetainedNodalDofsBC(name=BC_name,
				createStepName=stepName_Sub, region=region, u1=U[0], u2=U[1],
				u3=U[2], ur1=U[3], ur2=U[4], ur3=U[5])
			i+=1
	else:
		#Retained nodes not specified, retain all boundary nodes
		print('here')
		retainBCs(modelData=modelData,dim=dim)
	#Create job, write input
	mdb.Job(name=jobName, model=modelName_Sub,
		description='', type=ANALYSIS, atTime=None, waitMinutes=0, waitHours=0,
		queue=None, memory=90, memoryUnits=PERCENTAGE, getMemoryFromAnalysis=True,
		explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE, echoPrint=OFF,
		modelPrint=OFF, contactPrint=OFF, historyPrint=OFF, userSubroutine='',
		scratch='', resultsFormat=ODB, multiprocessingMode=DEFAULT, numCpus=1,
		numGPUs=0)
	mdb.jobs[jobName].writeInput(consistencyChecking=OFF)

	#Modify input file with a substructure matrix generation (for non-linear use)
	# string = '*SUBSTRUCTURE MATRIX OUTPUT, OUTPUT FILE=USER DEFINED,\
	# FILE NAME = '+matricesFile+', RECOVERY MATRIX=YES, STIFFNESS=YES'

	# fileName = jobName+'.inp'

	# for line in fileinput.input(fileName,inplace=1):
		# print line,
		# if '*Damping Controls' in line:
			# print string
	# fileinput.close()

	strCommandLine = 'abaqus job='+jobName+' ask_delete=OFF'
	os.system(strCommandLine)	
	
	# To wait for completion before next loop iteration
	return jobName

def getSetSize(*args): 
	n = 1
	for arg in args:
		n *= len(arg)
	return n

i=1
	
	
# thetaSet = np.array([0,90])
cornerSize = 0.18 # portion of substructure width
thick13set = np.arange(0.05,0.21,0.05)	# Max is about cornerSize to mesh (geometrically, must be less than cornerSize*sqrt(2))
thick24set = np.arange(0.05,0.21,0.05)	# Max is about cornerSize to mesh (geometrically, must be less than cornerSize*sqrt(2))
filletSet = np.arange(0.04,0.18,0.045)				# For cornerSize=0.2, min=0.04, max = 0.18
materials = np.array(['Titanium Alpha-Beta'])#'Aluminum 2219','Kovar Steel','Titanium Alpha-Beta'])

nSubs = getSetSize(thick13set, thick24set, filletSet, materials)

sectionSet = np.array(['StiffShell','FlexibleShell'])
#materialRef = {materials[0]:'E=7e10 Pa\trho=2840 kg/m^3',materials[1]:'E=135e9 Pa\trho=8320 kg/m^3',materials[2]:'E=113e9 Pa\trho=4430 kg/m^3'}

width = dim[3]-dim[0]


# Note: While file being used is CrossAsymmetric.cae, code and cae file use "Cross" to reference part
modelData = {
	'modelName':'Model-1',
	'partName':'Cross',
	'stepName':'Step-1',
	'dim':dim}

counter = 1
fileDataName = 'CrossAsymmetricDataPoints.csv'

with open(fileDataName, 'wb') as csvfile:
		nSubsHeader = '%s,%d\n' % ('No. of substructures',nSubs)
		csvfile.write(nSubsHeader)	# Writes number of substructures generated for importSubstructure in Assembly code

		
		bounds = '%s,%s\n%s,%f,%s,%f,%s,%f\n%s,%f,%s,%f,%s,%f\n%s,%f,%s,%f,%s,%f\n%s,%f\n' % ('DV Bounds:','Units: SI (m)',
		'Thick13  Min:', thick13set[0]*width, ' Max:',thick13set[-1]*width, ' Step:',(thick13set[-1]*width-thick13set[0]*width)/(thick13set.size-1),
		'Thick24  Min:', thick24set[0]*width, ' Max:',thick24set[-1]*width, ' Step:',(thick24set[-1]*width-thick24set[0]*width)/(thick24set.size-1),
		'Fillet	 Min:', filletSet[0]*width, ' Max:',filletSet[-1]*width, ' Step:',(filletSet[-1]*width-filletSet[0]*width)/(filletSet.size-1),
		'CornerSize: ', cornerSize*width)
		csvfile.write(bounds)
		headers = '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % (
		'Substructure','ID','Material','K_xy','K_y','K_theta','mass','maxMises1','maxMises2','maxMises3','Thick13','Thick24','Fillet')
		csvfile.write(headers)

for material in materials:				
	for thick13 in thick13set:
		for thick24 in thick24set:
			for fillet in filletSet:
				Mdb()
				openMdb(model)			
				
				changeMaterial(sectionSet[0],material)
				dim = modifyDimensions()
				modifyCross(model=model,cornerSize=cornerSize,thick13=thick13,thick24=thick24,fillet=fillet)

				# force = analysisStep(model,dim,theta=theta,thickness = thickness )
				meshCross(model=model, globalSeed=0.021*width) #Need to change maybe
				#Run a substructure generation step in parallel 
				subJobName = substructureModel(modelData,i=counter,matricesFile = 'MATRICES')
				time.sleep(45)
				# Counter increment moved here to potentially avoid substructure generation issues
				counter += 1
				#Change after this point
				
				createAnalyticalSurface(model=model,dim=dim)
				instanceAnalyticalSurface(model,dim)
				defineRigidBody(model,dim)
				
				tieBody_and_Part(model,dim)
				modifyStep(model)
				encastreBottom(model,dim)
				postProcessingSets(model,dim)
				
				# Stiffness k_x
				xDisplacement(model,5e-4,width)
				xDisplacementJob = createJob(model=model,jobName='X_DISP')
				mdb.jobs[xDisplacementJob].submit(consistencyChecking=OFF)
				mdb.jobs[xDisplacementJob].waitForCompletion()
				K_xy,maxMises1 = odbPostProcess(xDisplacementJob,loadFlag=1)
				
				# Stiffness k_y
				mdb.models['Model-1'].boundaryConditions['MOVE_RP'].setValues(u1=0.0, u2=(5e-4)*(dim[4]-dim[1]))
				yDisplacementJob = createJob(model=model,jobName='Y_DISP')
				mdb.jobs[yDisplacementJob].submit(consistencyChecking=OFF)
				mdb.jobs[yDisplacementJob].waitForCompletion()
				K_y,maxMises2 = odbPostProcess(yDisplacementJob,loadFlag=2)
				
				# Stiffness k_theta
				mdb.models['Model-1'].boundaryConditions['MOVE_RP'].setValues(u2=0.0, ur3=0.01) # In degress at the moment, need to check if it needs to be in radians
				thetaRotationJob = createJob(model=model,jobName='THETA_ROT')
				mdb.jobs[thetaRotationJob].submit(consistencyChecking=OFF)
				mdb.jobs[thetaRotationJob].waitForCompletion()
				K_theta,maxMises3 = odbPostProcess(thetaRotationJob,loadFlag=3)
				
				# Query mass
				mass = mdb.models['Model-1'].parts['Cross'].getMassProperties()['mass']
				
				# Wait for substructure job to finish, hopefully will fix every other substructure generating
				mdb.jobs[subJobName].waitForCompletion()
				
				with open(fileDataName, 'ab') as csvfile:
					# Writing all relevant data to a CSV
					txt = '%s,%i,%s,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f\n' % (
					'CrossAsymmetric',counter,material,K_xy,K_y,K_theta,mass,maxMises1,maxMises2,maxMises3,thick13,thick24,fillet)
					csvfile.write(txt)
				
				
end = time.time()

print("--- %s seconds ---" % (end - start))
