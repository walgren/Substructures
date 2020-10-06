# -*- coding: mbcs -*-
#
# Abaqus/CAE Release 2018 replay file
# Internal Version: 2017_11_07-11.21.41 127140
# Run by sebastian.chirinos on Thu Jul 16 12:53:05 2020
#

# from driverUtils import executeOnCaeGraphicsStartup
# executeOnCaeGraphicsStartup()
#: Executing "onCaeGraphicsStartup()" in the site directory ...
from abaqus import *
from abaqusConstants import *
session.Viewport(name='Viewport: 1', origin=(0.0, 0.0), width=79.6100006103516, 
    height=120.839996337891)
session.viewports['Viewport: 1'].makeCurrent()
session.viewports['Viewport: 1'].maximize()
from caeModules import *
from driverUtils import executeOnCaeStartup
executeOnCaeStartup()
openMdb('Cross.cae')
#: The model database "C:\Users\sebastian.chirinos\O-REU\Attribute Space\XYdisplacement_CrossAsymmetric\FindingEdges\Cross.cae" has been opened.
session.viewports['Viewport: 1'].setValues(displayedObject=None)
session.viewports['Viewport: 1'].partDisplay.geometryOptions.setValues(
    referenceRepresentation=ON)
p = mdb.models['Model-1'].parts['Cross']
session.viewports['Viewport: 1'].setValues(displayedObject=p)
session.viewports['Viewport: 1'].partDisplay.setValues(mesh=ON)
session.viewports['Viewport: 1'].partDisplay.meshOptions.setValues(
    meshTechnique=ON)
session.viewports['Viewport: 1'].partDisplay.geometryOptions.setValues(
    referenceRepresentation=OFF)
session.viewports['Viewport: 1'].view.setValues(nearPlane=56.9265, 
    farPlane=95.494, width=48.4755, height=28.1936, viewOffsetX=9.05826, 
    viewOffsetY=0.430513)
p = mdb.models['Model-1'].parts['Cross']
e = p.edges
pickedEdges = e.getSequenceFromMask(mask=('[#777e739c #ff7 ]', ), )
p.seedEdgeBySize(edges=pickedEdges, size=0.25, deviationFactor=0.1, 
    minSizeFactor=0.1, constraint=FINER)
session.viewports['Viewport: 1'].view.setValues(nearPlane=57.8631, 
    farPlane=94.5574, width=38.4699, height=22.3743, viewOffsetX=7.26433, 
    viewOffsetY=-0.0559703)
p = mdb.models['Model-1'].parts['Cross']
p.generateMesh()
session.viewports['Viewport: 1'].view.setValues(nearPlane=64.8104, 
    farPlane=87.6101, width=2.35165, height=1.36773, viewOffsetX=-4.04544, 
    viewOffsetY=-3.89823)
session.viewports['Viewport: 1'].view.setValues(session.views['Front'])
