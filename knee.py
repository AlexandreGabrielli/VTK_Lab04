# coding=utf-8
import vtk
import time
import math
import os
import sys

# bibliothéque pour facilité l'utilisation des couleurs dans vtk
colors = vtk.vtkNamedColors()


def read_slc_file(filepath):
    """ read a slc file

    :param filepath: path of the file
    :return: vtkSLCReader
    """
    reader = vtk.vtkSLCReader()
    reader.SetFileName(filepath)
    reader.Update()
    # print(reader)
    return reader


def save_polydata(path, polydata):
    """ save a polydata into .vtk

    :param path: path you wanna save the file
    :param polydata: polydata you wanna save
    :return:
    """
    # exemple de writter https://vtk.org/Wiki/VTK/Examples/Cxx/IO/WriteVTP
    try:
        writter = vtk.vtkPolyDataWriter()
        writter.SetFileName(path)
        writter.SetInputConnection(polydata.GetOutputPort())
        writter.Update()
    except:
        print("Le polydata n'a pas pu être sauvegarder : ")
        print(sys.exc_info()[2])


def read_polydata(path):
    """ read a polydata from vtk file

    :param path: path to the file
    :return:
    """
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(path)
    reader.Update()
    return reader.GetOutput()


def clip(vtkalgorihtm, function, color):
    clipper = vtk.vtkClipPolyData()
    clipper.SetInputConnection(vtkalgorihtm.GetOutputPort())
    clipper.SetClipFunction(function)
    clipper.Update()

    # Skin mapper and actor
    mapper = vtk.vtkDataSetMapper()
    mapper.SetInputConnection(clipper.GetOutputPort())
    mapper.ScalarVisibilityOff()

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(color)

    return actor


def assembly_tube_view(reader, actorBone, algoSkin, outlineActor):
    """ this serve the up left view

    the skin is visible only in the form of tubes cutting the skin surface
    horizontally every centimetre

    :param reader: vtkSLCReader
    :param actorBone: a vtkactor representing the bone
    :param algoSkin:a vtkalgorithme representing the skin
    :param outlineActor: a vtkactor representing the outline rectangle
    :return: an assembly of all actor for this view
    """
    bounds = algoSkin.GetOutput().GetBounds()

    plane = vtk.vtkPlane()
    high = plane.EvaluateFunction((bounds[1] + bounds[0]) / 2.0,
                                  (bounds[3] + bounds[2]) / 2.0,
                                  bounds[5])

    # Create the tubes
    cutter = vtk.vtkCutter()
    cutter.SetCutFunction(plane)
    cutter.SetInputConnection(algoSkin.GetOutputPort())
    cutter.GenerateValues(math.floor(reader.GetDataExtent()[5] * reader.GetDataSpacing()[2] / 10) + 1, 0, high)

    tubeFilter = vtk.vtkTubeFilter()
    tubeFilter.SetInputConnection(cutter.GetOutputPort())
    tubeFilter.SetRadius(1)
    tubeFilter.SetNumberOfSides(1000)

    mapper_skin = vtk.vtkDataSetMapper()
    mapper_skin.SetInputConnection(tubeFilter.GetOutputPort())
    mapper_skin.ScalarVisibilityOff()

    # actor skin
    actorSkin = vtk.vtkActor()
    actorSkin.SetMapper(mapper_skin)
    actorSkin.GetProperty().SetColor(colors.GetColor3d("pink"))

    # Group the actors
    assembly = vtk.vtkAssembly()
    assembly.AddPart(actorSkin)
    assembly.AddPart(actorBone)
    assembly.AddPart(outlineActor)

    return assembly


def assembly_semi_transparency(actorBone, algoSkin, sphere, outlineActor):
    """ this serve the up right view

    bone and skin in realistic colors.
    The skin is semi-transparent on the front side and opaque on the back side.
    It is clipped by a sphere so that the joint is visible.

    :param actorBone: a vtkactor representing the bone
    :param algoSkin: a vtkalgorithme representing the skin
    :param sphere: a vtkalgorithme representing the sphere
    :param outlineActor: a vtkactor representing the outline rectangle
    :return:  an assembly of all actor for this view
    """
    actorSkinFront = clip(algoSkin, sphere, colors.GetColor3d("pink"))
    actorSkinFront.GetProperty().SetFrontfaceCulling(True)

    actorSkintBack = clip(algoSkin, sphere, colors.GetColor3d("pink"))
    actorSkintBack.GetProperty().SetBackfaceCulling(True)
    actorSkintBack.GetProperty().SetOpacity(0.5)

    assembly = vtk.vtkAssembly()
    assembly.AddPart(actorSkintBack)
    assembly.AddPart(actorSkinFront)
    assembly.AddPart(actorBone)
    assembly.AddPart(outlineActor)

    return assembly


def assembly_transparence_Skin(actorBone, algoSkin, sphere, outlineActor):
    """ this serve the down right view

    bone and skin in realistic colors.
    the skin is completely opaque and the sphere used for the clipper
    is visible in transparency

    :param actorBone: a vtkactor representing the bone
    :param algoSkin: a vtkalgorithme representing the skin
    :param sphere: a vtkalgorithme representing the sphere
    :param outlineActor: a vtkactor representing the outline rectangle
    :return:  an assembly of all actor for this view
    """

    # pour la sphere exemple https://www.paraview.org/Wiki/VTK/Examples/Python/Implicit/Sphere
    theSphere = vtk.vtkImplicitBoolean()
    theSphere.SetOperationTypeToDifference()
    theSphere.AddFunction(sphere)

    # Display the sphere
    SFsphere = vtk.vtkSampleFunction()
    SFsphere.SetImplicitFunction(theSphere)
    SFsphere.SetModelBounds(-1000, 1000, -1000, 1000, -1000, 1000)
    SFsphere.SetSampleDimensions(100, 100, 100)

    CFsphere = vtk.vtkContourFilter()
    CFsphere.SetInputConnection(SFsphere.GetOutputPort())

    mapperSphere = vtk.vtkPolyDataMapper()
    mapperSphere.SetInputConnection(CFsphere.GetOutputPort())
    mapperSphere.ScalarVisibilityOff()

    actorSphere = vtk.vtkActor()
    actorSphere.SetMapper(mapperSphere)
    actorSphere.GetProperty().SetColor(colors.GetColor3d("orange"))
    actorSphere.GetProperty().SetOpacity(0.1)

    actorSkin = clip(algoSkin, sphere, colors.GetColor3d("pink"))

    # Group the actors
    assembly = vtk.vtkAssembly()
    assembly.AddPart(actorSkin)
    assembly.AddPart(actorBone)
    assembly.AddPart(actorSphere)
    assembly.AddPart(outlineActor)

    return assembly


def assembly_bone_skin_distance(algoBone, algoSkin, outlineActor):
    """ this serve the down left view

    only the surface of the bone can be seen, but it is coloured to show
    the distance between each point on the bone and the skin

    :param algoBone:  a vtkalgorithme representing the bone
    :param algoSkin:  a vtkalgorithme representing the skin
    :param outlineActor: a vtkactor representing the outline rectangle
    :return:  an assembly of all actor for this view
    """
    SAVE_MODEL = "./data/model.vtk"

    if os.path.isfile(SAVE_MODEL):
        print("model already save")
        dataFilter = vtk.vtkCleanPolyData()
        dataFilter.SetInputData(read_polydata(SAVE_MODEL))
        dataFilter.Update()
    else:
        dataFilter = vtk.vtkDistancePolyDataFilter()
        dataFilter.SetInputData(1, algoSkin.GetOutput())
        dataFilter.SetInputData(0, algoBone.GetOutput())
        dataFilter.Update()
        save_polydata(SAVE_MODEL, dataFilter)

    mapper = vtk.vtkPolyDataMapper()

    lut = mapper.GetLookupTable()
    lut.SetHueRange(2 / 3, 0)
    lut.Build()

    mapper.SetInputConnection(dataFilter.GetOutputPort())
    mapper.SetScalarRange(
        dataFilter.GetOutput().GetPointData().GetScalars().GetRange()[0],
        dataFilter.GetOutput().GetPointData().GetScalars().GetRange()[1]
    )
    actorBone = vtk.vtkActor()
    actorBone.SetMapper(mapper)
    actorBone.GetProperty().SetColor(colors.GetColor3d("white"))
    actorBone.GetProperty().SetBackfaceCulling(False)

    assembly = vtk.vtkAssembly()
    assembly.AddPart(actorBone)
    assembly.AddPart(outlineActor)

    return assembly


def main():
    """labo 4 : https://cyberlearn.hes-so.ch/mod/assign/view.php?id=1103056"""

    # le reader global du fichier slc
    reader = read_slc_file('./data/vw_knee.slc')

    # VtkAlgorithm pour les os
    algoBones = vtk.vtkMarchingCubes()
    algoBones.SetInputConnection(reader.GetOutputPort())
    algoBones.SetNumberOfContours(1)
    algoBones.SetValue(0, 73)
    algoBones.Update()
    # comme dans 3 renderer on utilise l'os tel qu'elle on creer déjà l'actor
    # afin de ne pas charger inutilement la ram
    mapper_bone = vtk.vtkDataSetMapper()
    mapper_bone.SetInputConnection(algoBones.GetOutputPort())
    mapper_bone.ScalarVisibilityOff()

    actorBone = vtk.vtkActor()
    actorBone.SetMapper(mapper_bone)
    actorBone.GetProperty().SetColor(colors.GetColor3d("white"))

    # vtkAlgorithm pour la peau
    algoSkin = vtk.vtkMarchingCubes()
    algoSkin.SetInputConnection(reader.GetOutputPort())
    algoSkin.SetNumberOfContours(1)
    algoSkin.SetValue(0, 52)
    algoSkin.Update()

    # implicite fonction pour la sphere
    sphere = vtk.vtkSphere()
    sphere.SetCenter(80, 120, 120)
    sphere.SetRadius(60)

    # create outline actor (same for all renderer)
    outline = vtk.vtkOutlineFilter()
    outline.SetInputConnection(reader.GetOutputPort())
    mapperOutline = vtk.vtkPolyDataMapper()
    mapperOutline.SetInputConnection(outline.GetOutputPort())
    outlineActor = vtk.vtkActor()
    outlineActor.SetMapper(mapperOutline)
    outlineActor.GetProperty().SetColor(colors.GetColor3d("black"))

    # create the 4 renderer
    # une caméra pour les réunir tous
    camera = vtk.vtkCamera()
    camera.SetPosition(-600, -5, 300)
    camera.SetFocalPoint(70, 70, 100)
    camera.Roll(-90)
    #camera.Azimuth(180)
    # parametre des 4 renderer
    renderers = {
        "renderer_0":
            {"color": colors.GetColor3d("cyan"),
             "dimension": [0, 0.5, 0, 0.5],
             "actor": assembly_transparence_Skin(actorBone, algoSkin, sphere, outlineActor)},

        "renderer_1":
            {"color": colors.GetColor3d("grey"),
             "dimension": [0.5, 1, 0, 0.5],
             "actor": assembly_bone_skin_distance(algoBones, algoSkin, outlineActor)},
        "renderer_2":
            {"color": colors.GetColor3d("pink"),
             "dimension": [0, 0.5, 0.5, 1],
             "actor": assembly_tube_view(reader, actorBone, algoSkin, outlineActor)},
        "renderer_3":
            {"color": colors.GetColor3d("green_pale"),
             "dimension": [0.5, 1, 0.5, 1],
             "actor": assembly_semi_transparency(actorBone, algoSkin, sphere, outlineActor)}
    }
    # on creer les 4 renderer et on les attache a la fenetre
    rw = vtk.vtkRenderWindow()
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(rw)
    for value in renderers.values():
        ren = vtk.vtkRenderer()
        ren.SetActiveCamera(camera)
        rw.AddRenderer(ren)
        dimension = value["dimension"]
        # print(dimension)
        ren.SetViewport(dimension[0], dimension[2], dimension[1], dimension[3])
        ren.SetBackground(value["color"])
        ren.AddActor(value["actor"])

    rw.SetSize(1024, 700)
    rw.Render()
    rw.SetWindowName('VTK: laboratoire 4')
    iren.Start()


if __name__ == '__main__':
    main()
