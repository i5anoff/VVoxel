import bpy
from bpy_extras.io_utils import ImportHelper
import itertools, math
import numpy as np
import os
import datetime
print(np.__version__)
now = datetime.datetime.now
from bpy_extras.io_utils import ExportHelper
from bpy.props import (
        StringProperty,
        IntProperty,
        FloatVectorProperty
        )
from bpy.types import (
        Operator,
        OperatorFileListElement,
        )
bl_info = {
    "name" : "VVoxel",
    "author" : "Allosteric",
    "version" : (1,0),
    "blender" : (2, 79, 0),
    "location" : "3DView > Object",
    "description" : "read numpy array and add voxel",
    "warning" : "",
    "support" : "TESTING",
    "wiki_url" : "",
    "tracker_url" : "",
    "category" : "Object",
}


def add_voxel(voxel, self):
    print("start")
    start = now()
    zerostart = np.zeros(np.add(voxel.shape,(2,2,2)),dtype=int)
    zerostart[1:-1,1:-1,1:-1] = voxel
    z_diff = np.diff(zerostart,axis=0)
    if z_diff[z_diff!=0].size > self.complexity*10000:
        return "TOO_MANY_VERTS"
    y_diff = np.diff(zerostart,axis=1)
    x_diff = np.diff(zerostart,axis=2)

    z_vs = vs(z_diff,"z")
    y_vs = vs(y_diff,"y")
    x_vs = vs(x_diff,"x")
    vs_ = np.concatenate((z_vs,y_vs,x_vs))
    vs_ = np.fliplr(vs_)
    fs = np.arange(len(vs_))
    vs_, fs = remove_doubles(vs_,fs)
    v_object = add_obj(vs_.tolist(),[],fs.reshape(fs.size//4,4).tolist(),"voxel")
    bvs = np.multiply(np.array(list(itertools.product(range(2),range(2),range(2)))),voxel.shape[::-1]).tolist()
    o_object = add_obj(bvs, np.matrix("0,1;0,2;0,4;1,3;1,5;2,3;2,6;3,7;4,5;4,6;5,7;6,7").tolist(),[],"outline")
    v_object.parent = o_object
    o_object.location = bpy.context.scene.cursor_location
    o_object.scale = self.rescale
    print("took {0}secs".format((datetime.datetime.now() - start).total_seconds()))
    return "FINISHED"
def add_obj(vs,es,fs,name):
    mesh_data = bpy.data.meshes.new(name+"_mesh_data")
    mesh_data.from_pydata(vs,es,fs)
    mesh_data.update()
    obj = bpy.data.objects.new(name+"_object", mesh_data)
    scene = bpy.context.scene
    scene.objects.link(obj)
    obj.select = True
    return obj

def vs(diff,axis):
    before = now()
    ds = diff.shape
    loc = np.mgrid[ds[0]-1:-1:-1,ds[1]-1:-1:-1,:ds[2]].astype(np.uint16)
    loc = np.swapaxes(np.rollaxis(loc,0,-1),-1,-2)
    flat_loc = loc.flatten().reshape(loc.size//3,3)
    del loc
    flat_diff = diff.flatten()
    del diff
    skip_loc = flat_loc[flat_diff!=np.array(0)]
    del flat_loc

    skip_diff = flat_diff[flat_diff != np.array(0)]
    del flat_diff
    minus_idx = np.where(skip_diff == -1)
    del skip_diff
    print(1,now()-before)
    before = now()
    result = np.empty(skip_loc.shape[:-1]+(4,3)).astype(np.uint16)
    around_off ={'z': [[0, -1, 0], [0, 0, 0], [0, 0, -1], [0, -1, -1]],
 'y': [[0, 0, 0], [-1, 0, 0], [-1, 0, -1], [0, 0, -1]],
 'x': [[0, -1, 0], [0, 0, 0], [-1, 0, 0], [-1, -1, 0]]}[axis]
    for i in range(4):
        for j in range(3):
            result[...,i,j] = around_off[i][j] + skip_loc[...,j]
    print(2,now()-before)
    before = now()
    result[minus_idx] = np.flip(result[minus_idx],1)
    result = result.flatten().reshape(result.size//3,3)
    print(3,now()-before)
    before = now()
    return result
def remove_doubles(vs,fs):
    print("number of vertices: ",len(vs))
    start = now()
    new_vs, inverse = np.unique(vs,return_inverse=True,axis=0)
    new_fs = inverse[fs]
    print("number of vertices: ",len(new_vs))
    print("remove doubles took: ",now()-start)
    return new_vs, new_fs

class AddVoxel(bpy.types.Operator,ImportHelper):
    bl_idname  = "object.add_voxel"
    bl_label = "Voxel From .npy"
    bl_description = "outputs the locations of the markers in the 3DView"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".npy"
    filter_glob = StringProperty(default="*.npy", options={'HIDDEN'})

    complexity = IntProperty(name="complexity", description = "Maximum computable complexity voxel", default = 10)
    rescale = FloatVectorProperty(name="rescale", description = "rescale the voxel", default=(1.0,1.0,1.0),subtype="XYZ")
    def execute(self, context):
        import os
        fname = bpy.path.abspath(self.properties.filepath)
        print("reading: ", fname)
        if os.path.isfile(fname):
            array3d = np.load(fname)
            if array3d.dtype != bool:
                self.report({"ERROR"}, "Please set a array of bool. It is currently: {0}".format(array3d.dtype))
                return {"CANCELLED"}
            result = add_voxel(array3d, self)
            if result =="FINISHED":
                return {'FINISHED'}
            elif result == "TOO_MANY_VERTS":
                self.report({"ERROR"},"The voxel is too complex.")
                return {"CANCELLED"}
        else:
            self.report({"ERROR"},"No such File")
            return{"CANCELLED"}
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


        return {"FINISHED"}
def menu_fn(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.separator()
    self.layout.operator(AddVoxel.bl_idname)
def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_add.append(menu_fn)

def unregister():
    bpy.types.INFO_MT_add.remove(menu_fn)
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
