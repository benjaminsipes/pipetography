# AUTOGENERATED! DO NOT EDIT! File to edit: 00_core.ipynb (unless otherwise specified).

__all__ = ['get_subs', 'filter_workflow', 'get_bfiles_tuple', 'get_sub_gradfiles', 'BIDS_metadata']

# Internal Cell
import os, sys
from nipype.interfaces.base import CommandLine, CommandLineInputSpec, File
from nipype.interfaces.base import TraitedSpec, traits
from nipype.interfaces.io import BIDSDataGrabber
from bids.layout import BIDSLayout
from itertools import product

import nibabel as nb
from nilearn import plotting
from nilearn.image import new_img_like

from nipype.interfaces import fsl
from nipype.interfaces.freesurfer.preprocess import ReconAll
from nipype.interfaces.mrtrix3.utils import BrainMask, TensorMetrics, DWIExtract, MRMath
from nipype.interfaces.mrtrix3.preprocess import MRDeGibbs, DWIBiasCorrect
from nipype.interfaces.mrtrix3.reconst import FitTensor

# Cell
def get_subs(BIDS_dir="BIDS_dir"):
    """
    Gets list of subjects in a BIDS directory, by default it looks in "data" folder in your CWD
    Input str of path to BIDS dir otherwise
    """
    print(
        "Creating layout of data directory, might take a while if there are a lot of subjects"
    )
    layout = BIDSLayout(BIDS_dir)
    sub_list = layout.get_subjects()
    ses_list = layout.get_sessions()
    return sub_list, ses_list, layout

# Cell
def filter_workflow(BIDS_dir, sub_list, ses_list, exclude_list):
    all_sub_ses_combos = set(product(sub_list, ses_list))
    missing_list = []
    for combo in all_sub_ses_combos:
        sub_ses_dir = os.path.join(BIDS_dir, 'sub-'+combo[0], 'ses-'+combo[1])
        if not os.path.exists(sub_ses_dir):
            missing_list.append(combo)

    filtered_sub_ses_list = list(all_sub_ses_combos - set(missing_list) - set(exclude_list))
    sub_iter = [tup[0] for tup in filtered_sub_ses_list]
    ses_iter = [tup[1] for tup in filtered_sub_ses_list]
    return sub_iter, ses_iter

# Cell
def get_bfiles_tuple(in_List):
    """
    Input list of paths to [bval, bvec] files in FSL format. (Deprecated)
    """
    # bvs = layout.get(subject = sub_list[0], suffix = 'dwi', session = 1, extensions = ['bvec', 'bval'], return_type = 'file')
    bvs_tuple = tuple(in_List)[::-1]
    return bvs_tuple

# Cell
def get_sub_gradfiles(sub_dwi, ext = 'nii.gz'):
    import os, sys
    """
    For a given layout and a subject's DWI, grab the matching gradient files
    """
    sub_bvec = sub_dwi.replace(ext, 'bvec')
    sub_bval = sub_dwi.replace(ext, 'bval')
    if os.path.exists(sub_bvec) and os.path.exists(sub_bval):
        grad_files = tuple([sub_bvec, sub_bval])
        return grad_files
    else:
        sys.exit('Gradient files missing for {}'.format(sub_dwi))

# Cell

def BIDS_metadata(path, bids_dir):
    PEDIR = None
    from bids.layout import BIDSLayout
    bids_layout =  BIDSLayout(bids_dir)
    # total read out itme
    try:
        TRT = bids_layout.get_metadata(path)['TotalReadoutTime']
    except:
        print('No totalreadouttime in BIDS DWI JSON file, setting to default 0.1')
        TRT = 0.1
    # phase encoding direction
    try:
        PEDIR = bids_layout.get_metadata(path)['PhaseEncodingDirection']
    except KeyError:
        print('No phase encoding direction in JSON! Please add to all DWI JSON')

    return TRT, PEDIR

# Internal Cell
class PipetographyBaseInputSpec(CommandLineInputSpec):
    export_grad = traits.Str(
        argstr="-export_grad_mrtrix %s",
        desc="export new gradient files in mrtrix format",
    )
    export_fslgrad = traits.Tuple(
        (traits.Str, traits.Str),
        argstr="-export_grad_fsl %s %s",
        desc="export gradient files in fsl format",
    )
    grad_fsl = traits.Tuple(
        (traits.Str, traits.Str),
        argstr="-fslgrad %s %s",
        desc="provide gradient table in fsl format",
        xor=["grad_file"]
    )
    grad_file = File(
        exists=True,
        argstr="-grad %s",
        desc="dw gradient scheme (MRTrix format)",
        xor=["grad_fsl"],
    )
    nthreads = traits.Int(
        argstr="-nthreads %d",
        desc="number of threads for mrtrix functions only. If zero, multi-threading is disabled",
        nohash=True,
    )
    force = traits.Bool(
        argstr="-force", desc="force output file if the file already exits"
    )
    quiet = traits.Bool(
        argstr="-quiet", desc="suppress verbose outputs"
    )

# Internal Cell
class MRCatInputSpec(CommandLineInputSpec):
    """inputs to mrtrix3's mrcat"""
    image1 = File(
        exists=True, mandatory=True, argstr="%s", position=1, desc="first input image"
    )
    image2 = File(
        exists=True, mandatory=True, argstr="%s", position=2, desc="additional input image"
    )
    out_file = File(
        mandatory=True, argstr="%s", position =3, desc="output image"
    )

class MRCatOutputSpec(TraitedSpec):
    """mrcat output file spec"""
    out_file = File(argstr="%s", desc="output image")

class MRCat(CommandLine):
    "Concatenate images"
    _cmd = "mrcat"
    input_spec = MRCatInputSpec
    output_spec = MRCatOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

class GradCatInputSpec(CommandLineInputSpec):
    grad1 = File(
        argstr="%s", position = 1, desc="first gradient"
    )
    grad2 = File(
        argstr="%s", position = 2, desc="second gradient"
    )
    out_file = File(
        argstr="> %s", position = 3, desc="output gradient"
    )

class GradCatOutputSpec(TraitedSpec):
    """concatenated gradient file"""
    out_file = File(argstr="%s", desc="output gradient")

class GradCat(CommandLine):
    """concatenate gradients"""
    _cmd = "cat"
    input_spec = GradCatInputSpec
    output_spec = GradCatOutputSpec

    def  _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell
class aff2rigidInputSpec(CommandLineInputSpec):
    """
    Specifying inputs to fsl's aff2rigid
    """
    in_file = File(
        exists=True, mandatory=True, argstr="%s", position=1, desc="FLIRT transform (12 DOF) from the input image to standard"
    )
    out_file = File(
        manndatory=True, argstr="%s", position=2, desc="output matrix which will go from the input image to standard space (6 DOF)"
    )

class aff2rigidOutputSpec(TraitedSpec):
    """
    Specifying outputs of aff2rigid
    """
    out_file = File(argstr="%s", desc="output matrix")

class fslaff2rigid(CommandLine):
    """
    Align cropped image the ACPC plane using FSL's aff2rigid
    """
    _cmd = "aff2rigid"
    input_spec = aff2rigidInputSpec
    output_spec = aff2rigidOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell
class ConvertInputSpec(PipetographyBaseInputSpec):
    in_file = File(
        exists=True, argstr="%s", mandatory=True, position=1, desc="input image"
    )
    out_file = File(
        "dwi.mif",
        argstr="%s",
        mandatory=True,
        position=2,
        usedefault=True,
        desc="output image",
    )
    coord = traits.List(
        traits.Int,
        sep=" ",
        argstr="-coord %s",
        desc="extract data at the specified coordinates",
    )
    vox = traits.List(
        traits.Float, sep=",", argstr="-vox %s", desc="change the voxel dimensions"
    )
    axes = traits.List(
        traits.Int,
        sep=",",
        argstr="-axes %s",
        desc="specify the axes that will be used",
    )
    scaling = traits.List(
        traits.Float,
        sep=",",
        argstr="-scaling %s",
        desc="specify the data scaling parameter",
    )
    export_json = traits.Bool(
        argstr="-json_export",
        desc="export image header to JSON file",
        position = -2
    )
    out_json = File(
        argstr="%s",
        desc="exported JSON file name",
        position = -1
    )

class ConvertOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="output image")
    out_bfile = File(desc="exported gradient file")
    out_fslbvec=File(desc="exported fsl gradient bvecs")
    out_fslbval=File(desc="exported fsl gradient bvals")
    out_json = File(desc="JSON with image header info")


class Convert(CommandLine):
    _cmd = "mrconvert"
    input_spec = ConvertInputSpec
    output_spec = ConvertOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        inputs = self.input_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        if self.inputs.export_grad:
            outputs["out_bfile"] = os.path.abspath(self.inputs.export_grad)
        if self.inputs.export_fslgrad:
            outputs["out_fslbvec"] = os.path.abspath(self.inputs.export_fslgrad[0])
            outputs["out_fslbval"] = os.path.abspath(self.inputs.export_fslgrad[1])
        if self.inputs.export_json:
            outputs["out_json"] = os.path.abspath(self.inputs.out_json)

        return outputs

# Internal Cell
class GradCheckInputSpec(PipetographyBaseInputSpec):
    in_file = File(
        exists=True,
        mandatory=True,
        argstr = '%s',
        position = 1,
        desc = "input DWI"
    )
    mask_file = File(
        exists=True,
        argstr="-mask %s",
        position = 3,
        desc = "input brain mask image option"
    )
    tract_number = traits.Int(
        argstr="-number %d",
        desc="number of tracts generated for each test",
        nohash=True,
    )

class GradCheckOutputSpec(TraitedSpec):
    out_bfile = File(
        argstr='%s', desc = "corrected gradient file"
    )

class GradCheck(CommandLine):
    """
    Check the input DWI's gradients with a provided brain mask and output the corrected gradients
    """
    _cmd = "dwigradcheck"
    input_spec = GradCheckInputSpec
    output_spec = GradCheckOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_bfile"] = os.path.abspath(self.inputs.export_grad)
        return outputs

# Internal Cell
class dwidenoiseInputSpec(PipetographyBaseInputSpec):
    """
    Specifying inputs to dwidenoise
    """

    in_file = File(
        exists=True, mandatory=True, argstr="%s", position=1, desc="input image"
    )
    noise = File(
        mandatory=True, argstr="-noise %s", position=2, desc="output noise map"
    )
    out_file = File(
        mandatory=True, argstr="%s", position=-1, desc="output denoised image"
    )


class dwidenoiseOutputSpec(TraitedSpec):
    """
    Specifying outputs of dwidenoise
    """

    noise = File(argstr="%s", desc="output noise level map")
    out_file = File(argstr="%s", desc="output denoised file")


class dwidenoise(CommandLine):
    """
    Denoise DWI data with mrtrix3's dwidenoise.
    This should be performed as the first step of the preprocessing pipeline!
    Arguments:
        in_file (str): Input DWI image
        noise (str): output noise map
        out_file (str): output denoised image
        nthreads (int): number of threads to use
    """

    _cmd = "dwidenoise"
    input_spec = dwidenoiseInputSpec
    output_spec = dwidenoiseOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["noise"] = os.path.abspath(self.inputs.noise)
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell
class dwipreprocInputSpec(PipetographyBaseInputSpec):
    in_file = File(
        exists=True,
        mandatory=True,
        argstr="%s",
        position=0,
        desc="input denoised, Gibbs artifact removed file",
    )
    rpe_options = traits.Str(
        mandatory=True,
        argstr="%s",
        position=3,
        desc="acquisition phase-encoding design",
    )
    pe_dir = traits.Str(
        mandatory=True, argstr="-pe_dir %s", position=4, desc="phase encoding direction"
    )
    eddy_options = traits.Str(
        mandatory=False,
        argstr="-eddy_options %s",
        position=2,
        desc="eddy command options within quotation marks and contains at least one space",
    )
    out_file = File(
        mandatory=True,
        argstr="%s",
        position=1,
        desc="output denoised, corrected, preproc image",
    )
    RO_time = traits.Float(
        argstr='-readout_time %f',
        position=-1,
        desc='total read out time, if unspecified defaults to 0.1'
    )


class dwipreprocOutputSpec(TraitedSpec):
    out_file = File(argstr="%s", desc="output denoised, corrected, preproc image")
    out_bfile = File(argstr="%s", desc="eddy corrected gradients")


class dwipreproc(CommandLine):
    """
    mrtrix3 dwipreproc for motion/eddy current correction
    Arguments:
        in_file (str): input file that needs the artifact correction
        rpe_options (str): phase-encoding design, see mrtrix3's dwipreproc for detail options
        pe_dir (str): phase encoding directions, see mrtrix3's dwipreproc for detail options
        eddy_options (str): eddy current correction options. see mrtrix3's dwipreproc for detail options
        nthreads (int): number of threads used
        grad_fsl (tuple): bvec/bval files
        out_file (str): file name and path for output
    Returns:
        out_file (str): preprocessed file, this is the input to tractography.
    """

    _cmd = "dwifslpreproc"
    input_spec = dwipreprocInputSpec
    output_spec = dwipreprocOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        if self.inputs.export_grad:
            outputs["out_bfile"] = os.path.abspath(self.inputs.export_grad)
        return outputs

# Internal Cell
class BiasCorrectInputSpec(PipetographyBaseInputSpec):
    in_file = File(
        exists=True, argstr="%s", position=1, mandatory=True, desc="input DWI image"
    )
    in_mask = File(argstr="-mask %s", desc="input mask image for bias field estimation")
    use_ants = traits.Bool(
        argstr="ants",
        mandatory=True,
        desc="use ANTS N4 to estimate the inhomogeneity field",
        position = 0,
        xor=["use_fsl"],
    )
    use_fsl = traits.Bool(
        argstr="fsl",
        mandatory=True,
        desc="use FSL FAST to estimate the inhomogeneity field",
        position = 0,
        xor=["use_ants"],
    )
    bias = File(argstr="-bias %s", desc="bias field")
    out_file = File(
        name_template="%s_biascorr",
        name_source="in_file",
        keep_extension=True,
        argstr="%s",
        position=2,
        desc="the output bias corrected DWI image",
        genfile=True,
    )
    args = traits.Str(
        argstr="%s",
        desc="additional arguments to ANTS or FSL",
        position=1
    )


class BiasCorrectOutputSpec(TraitedSpec):
    bias = File(desc="the output bias field", exists=True)
    out_file = File(desc="the output bias corrected DWI image", exists=True)


class BiasCorrect(CommandLine):
    _cmd = "dwibiascorrect"
    input_spec = BiasCorrectInputSpec
    output_spec = BiasCorrectOutputSpec
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        outputs['bias'] = os.path.abspath(self.inputs.bias)
        # Get the attribute saved during _run_interface
        return outputs

# Internal Cell
class MRInfoInputSpec(PipetographyBaseInputSpec):
    in_file = File(
        exists=True, argstr="%s", position=1, mandatory=True, desc="input DWI image"
    )
    args = traits.Str(
        argstr="%s",
        desc="options arguments to mrinfo",
        position=0
    )

class MRInfoOutputSpec(TraitedSpec):
    out_bfile = File(
        argstr='%s', desc = "Output gradient file"
    )

class MRInfo(CommandLine):
    _cmd = "mrinfo"
    input_spec = MRInfoInputSpec
    output_spec = MRInfoOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        try:
            outputs["out_bfile"] = os.path.abspath(self.inputs.export_grad)
        except:
            print('There is no output gradient file')
        return outputs

# Internal Cell
class CheckFiniteInputSpec(PipetographyBaseInputSpec):
    out_file = File(
        mandatory=True, argstr="%s", position=4, desc="output file name"
    )
    isfinite = traits.Str(
        argstr = "%s -finite",
        desc = "Not NaN or Inf per voxel",
        position = 1
    )

class CheckFiniteOutputSpec(TraitedSpec):
    out_file = File(desc = "output file", exists=True)

class CheckFinite(CommandLine):
    _cmd = "mrcalc"
    input_spec = CheckFiniteInputSpec
    output_spec = CheckFiniteOutputSpec
    def _list_outputs(self):
        outputs = self.output_spec().get()
        return outputs

class CompareIfInputSpec(PipetographyBaseInputSpec):
    out_file = File(
        mandatory=True, argstr="%s", position=4, desc="output file name"
    )
    cond_if = traits.Str(
        argstr = "%s 0 -if",
        desc = "If first one is true, return second, if not return third",
        position = 1
    )

class CompareIfOutputSpec(TraitedSpec):
    out_file = File(desc = "output file",  exists=True)

class CompareIf(CommandLine):
    _cmd = "mrcalc"
    input_spec = CompareIfInputSpec
    output_spec = CompareIfOutputSpec
    def _list_outputs(self):
        outputs = self.output_spec().get()
        return outputs

# Internal Cell
class CheckNIZInputSpec(PipetographyBaseInputSpec):
    in_file = File(
        exists=True, argstr="%s", position=0, desc="input image"
    )
    out_file = File(
        mandatory=True, argstr="%s", position=4, desc="output file name", genfile=True
    )
    isfinite = traits.Str(
        argstr="%s -finite",
        desc="not NaN or Inf",
        position=1
    )
    cond_if = traits.Str(
        argstr="%s 0 -if",
        desc="return operand that's True",
        position=2
    )
    args = traits.Str(
        argstr="%s",
        desc="options arguments to mrcalc",
        position=3
    )

class CheckNIZOutputSpec(TraitedSpec):
    out_file = File(desc = "Output file", exists=True)

class CheckNIZ(CommandLine):
    _cmd = "mrcalc"
    input_spec = CheckNIZInputSpec
    output_spec = CheckNIZOutputSpec
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell
class RicianNoiseInputSpec(PipetographyBaseInputSpec):
    in_file = File(
        exists=True, argstr="%s", position=0, mandatory=True, desc="input dwi image"
    )
    power = traits.Int(
        argstr="%d -pow",
        position = 1,
        desc = "raise to the power of"
    )
    lownoisemap = File(
            exists=True, argstr="%s", position=2, desc="low noise map image"
    )
    denoise = traits.Int(
        argstr="%d -pow -sub -abs -sqrt",
        position=3,
        desc="denoise math operation"
    )
    out_file = File(
        argstr="%s", position=4, mandatory=True, desc="output DWI denoised image",
        genfile=True,
    )


class RicianNoiseOutputSpec(TraitedSpec):
    out_file = File(desc = "output DWI image", exists=True)


class RicianNoise(CommandLine):
    _cmd = "mrcalc"
    input_spec = RicianNoiseInputSpec
    output_spec = RicianNoiseOutputSpec
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell

class MRThresholdInputSpec(PipetographyBaseInputSpec):
    opt_abs = traits.Float(
        argstr="-abs %f",
        desc="absolute intensity",
        position=0,
        xor=["opt_per", "opt_top", "opt_bot"]
    )
    opt_per = traits.Float(
        argstr="-percentile %f",
        desc="percentile of image intensity",
        position=0,
        xor=["opt_abs", "opt_top", "opt_bot"]
    )
    opt_top = traits.Float(
        argstr="-top %f",
        desc="number of top-value image intensities",
        position=0,
        xor=["opt_abs", "opt_per", "opt_bot"]
    )
    opt_bot = traits.Float(
        argstr="-bot %f",
        desc="number of bottom valued voxels",
        position=0,
        xor=["opt_abs", "opt_top", "opt_per"]
    )
    in_file = File(
        exists=True,
        mandatory=True,
        argstr="%s",
        desc="input file path",
        position=1
    )
    out_file = File(
        argstr="%s",
        desc="output file path/name",
        position=2
    )

class MRThresholdOutputSpec(TraitedSpec):
    out_file = File(desc = "output thresholded image")

class MRThreshold(CommandLine):
    _cmd = "mrthreshold"
    input_spec = MRThresholdInputSpec
    output_spec = MRThresholdOutputSpec
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell
class DWINormalizeInputSpec(PipetographyBaseInputSpec):
    opt_intensity = traits.Float(
        argstr="-intensity %f",
        desc="Normalise the b=0 signal to a specified value (Default: 1000)",
        position=0,
    )
    opt_percent = traits.Int(
        argstr="-percentile %d",
        desc="Define the percentile of the b=0 image intensties within the mask used for normalisation",
        position=0,
    )
    in_file = File(
        exists=True,
        mandatory=True,
        argstr="%s",
        desc="input file path",
        position=1
    )
    mask_file = File(
        argstr="%s",
        desc="The mask within which a reference b=0 intensity will be sampled",
        position=2
    )
    out_file = File(
        argstr="%s",
        desc="output file path/name",
        position=3
    )

class DWINormalizeOutputSpec(TraitedSpec):
    out_file = File(desc = "output thresholded image")

class DWINormalize(CommandLine):
    _cmd="dwinormalise individual"
    input_spec=DWINormalizeInputSpec
    output_spec=DWINormalizeOutputSpec
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell

class TransConvertInputSpec(PipetographyBaseInputSpec):
    flirt_xfm = File(
        exists=True,
        argstr="%s",
        desc="flirt transformation matrix",
        position=0,
        xor = ['itk_xfm']
    )
    flirt_in = File(
        exists=True,
        argstr="%s",
        desc="flirt input file",
        position=1,
        xor = ['itk_xfm']
    )
    flirt_ref = File(
        exists=True,
        argstr="%s",
        desc="flirt reference image",
        position=2,
        xor = ['itk_xfm']
    )
    itk_xfm = File(
        exists=True,
        argstr="%s",
        desc="itk transformation file",
        position=0,
        xor=['flirt_xfm','flirt_in','flirt_ref']
    )
    flirt = traits.Bool(
        argstr="flirt_import",
        desc="Apply transformation conversion to flirt output",
        position = 3,
        xor=["itk"]
    )
    itk = traits.Bool(
        argstr="itk_import",
        desc="Apply transformation conversion to itk output",
        position=3,
        xor=["flirt"]
    )
    out_file = File(
        argstr="%s",
        mandatory=True,
        position=4,
        desc="output mrtrix3 transformation matrix"
    )

class TransConvertOutputSpec(TraitedSpec):
    out_file=File(desc="output mrtrix3 transformation matrix")

class TransConvert(CommandLine):
    _cmd = 'transformconvert'
    input_spec=TransConvertInputSpec
    output_spec=TransConvertOutputSpec
    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs


class MRTransformInputSpec(PipetographyBaseInputSpec):
    linear_xfm = File(
        argstr="-linear %s",
        position=0,
        desc="input linear affine transformation matrix"
    )
    in_file = File(
        argstr="%s",
        mandatory=True,
        position=1,
        desc="input image"
    )
    out_file = File(
        argstr="%s",
        mandatory=True,
        position=2,
        desc="output image"
    )

class MRTransformOutputSpec(TraitedSpec):
    out_file = File(desc="Transformed image")

class MRTransform(CommandLine):
    """Apply spatial transformations to an image"""
    _cmd = 'mrtransform'
    input_spec=MRTransformInputSpec
    output_spec=MRTransformOutputSpec
    def _list_outputs(self):
        outputs=self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell
class WMBinarizeInputSpec(CommandLineInputSpec):
    in_file = File(
        exists=True,
        mandatory=True,
        argstr="--i %s",
        desc="Input aseg.mgz freesurfer recon-all output",
        position=0,
    )
    out_file = File(
        argstr="--o %s",
        desc="output WM binary mask",
        position = 1
    )
    all_wm = traits.Bool(
        argstr="--all-wm",
        desc="set match vals to 2, 41, 77, 251-255, 7, and 46, (aseg for all WM)",
        position = 2
    )

class WMBinarizeOutputSpec(TraitedSpec):
    out_file = File(desc="Output white matter mask")

class WMBinarize(CommandLine):
    """
    mri_binarize
    """
    _cmd = 'mri_binarize'
    input_spec = WMBinarizeInputSpec
    output_spec = WMBinarizeOutputSpec
    def _list_outputs(self):
        outputs=self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell
class MRRegridInputSpec(PipetographyBaseInputSpec):
    in_file = File(
        exists=True,
        mandatory=True,
        argstr="%s",
        desc="Input file to be resliced",
        position=0,
    )
    regrid = File(
        exists=True,
        argstr="regrid -template %s",
        desc="Regrid to template voxel grid size",
        position=1
    )
    out_file = File(
        argstr="%s",
        desc="output image",
        position=2
    )
    args = traits.Str(
        argstr="%s",
        desc="additional arguments",
        position = -1
    )


class MRRegridOutputSpec(TraitedSpec):
    out_file = File(desc="Output image")


class MRRegrid(CommandLine):
    """
    `mrgrid`'s regrid option'
    """
    _cmd = 'mrgrid'
    input_spec = MRRegridInputSpec
    output_spec = MRRegridOutputSpec
    def _list_outputs(self):
        outputs=self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell
def mask2seedtuple(mask_file, grid_size):
    seed_grid_tuple = (
        mask_file,
        grid_size,
    )
    return seed_grid_tuple

# Internal Cell

class Make5ttFSLInputSpec(PipetographyBaseInputSpec):
    in_file = File(
        exists=True,
        argstr="%s",
        mandatory=True,
        position=-2,
        desc="input image"
    )
    t2_file = File(
        exists=True,
        argstr="-t2 %s",
        desc="Provide a T2-weighted image in addition to the default T1-weighted image"
    )
    out_file = File(
        argstr="%s",
        mandatory=True,
        position=-1,
        desc="output image"
    )
    mask = File(
        exists=True,
        argstr="-mask %s",
        desc="Manually provide a brain mask, rather than deriving one in the script"
    )
    premasked=traits.Bool(
        argstr="-premasked",
        desc="Indicate that brain masking has already been applied to the input image"
    )
    nocrop=traits.Bool(
        argstr="-nocrop",
        desc="Do NOT crop the resulting 5TT image to reduce its size"
    )
    sgm_amyg_hip=traits.Bool(
        argstr="-sgm_amyg_hipp",
        desc="Represent the amygdalae and hippocampi as sub-cortical grey matter in the 5TT image"
    )

class Make5ttFSLOutputSpec(TraitedSpec):
    out_file = File(argstr="%s", exists=True, desc="output image")

class Make5ttFSL(CommandLine):
    """
    Interface with Mrtrix3's 5ttgen command
    """
    _cmd="5ttgen fsl"
    input_spec=Make5ttFSLInputSpec
    output_spec=Make5ttFSLOutputSpec

    def _list_outputs(self):
        outputs=self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

class gmwmiInputSpec(CommandLineInputSpec):
    in_file = File(
        exists=True,
        mandatory=True,
        argstr="%s",
        position=-3,
        desc="Input 5 tissue type segmented anatomical file"
    )
    out_file = File(
        mandatory=True,
        argstr="%s",
        position=-2,
        desc="output mask image for the gm-wm interface",
    )
    in_mask = File(
        exists=True,
        argstr="-mask_in %s",
        position=1,
        desc="filtered mask, if not provided, the algorithm will use in_file only"
    )
    nthreads = traits.Int(
        argstr="-nthreads %d",
        desc="number of threads. if zero, the number" " of available cpus will be used",
        nohash=True,
    )
    force = traits.Bool(
        argstr="-force",
        desc="overwrite existing output file"
    )

class gmwmiOutputSpec(TraitedSpec):
    out_file=File(argstr="%s", desc="output mask image")

class gmwmi(CommandLine):
    """
    Interface with mrtrix3's 5tt2gmwmi command
    """
    _cmd="5tt2gmwmi"
    input_spec=gmwmiInputSpec
    output_spec=gmwmiOutputSpec

    def _list_outputs(self):
        outputs=self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell
class tckSIFT2InputSpec(CommandLineInputSpec):
    in_file = File(
        exists=True,
        mandatory=True,
        argstr="%s",
        position=-3,
        desc="input track file"
    )
    in_fod = File(
        exists=True,
        mandatory=True,
        argstr="%s",
        position=-2,
        desc="input image containing the spherical harmonics of the fiber orientation distributions"
    )
    out_file = File(
        mandatory=True,
        argstr="%s",
        desc="output weighting factor for each streamline",
        position=-1
    )
    proc_mask = File(
        exists=True,
        argstr="-proc_mask %s",
        desc="provide an image containing the processing mask weights for the model; image spatial dimensions must match the fixel image",
    )
    act = File(
        exists=True,
        argstr="-act %s",
        desc="use an ACT five-tissue-type segmented anatomical image to derive the processing mask",
    )
    fd_scale_gm = traits.Bool(
        argstr="-fd_scale_gm",
        desc="in conjunction with -act to heuristically downsize the fibre density estimates based on the presence of GM in the voxel. This can assist in reducing tissue interface effects when using a single-tissue deconvolution algorithm",
        requires=["act"]
    )
    nthreads = traits.Int(
        argstr="-nthreads %d",
        desc="number of threads. if zero, the number" " of available cpus will be used",
        nohash=True,
    )
    force = traits.Bool(
        argstr="-force",
        desc="overwrite existing output file"
    )

class tckSIFT2OutputSpec(TraitedSpec):
    out_file=File(argstr="%s", desc="output text file containing the weighting factor for each streamline")


class tckSIFT2(CommandLine):
    """
    Interface with mrtrix3 package
    Spherical-deconvolution informed filtering of tractograms - sift2
    Optimise per-streamline cross-section multipliers to match a whole-brain tractogram to fixel-wise fibre densities
    """
    _cmd="tcksift2"
    input_spec=tckSIFT2InputSpec
    output_spec=tckSIFT2OutputSpec

    def _list_outputs(self):
        outputs=self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs

# Internal Cell
class MakeConnectomeInputSpec(CommandLineInputSpec):
    """
    Specifying inputs to mrtrix3's tck2connectome
    """
    in_file = File(
        exists=True, mandatory=True, argstr="%s", position=-3, desc="input tck file"
    )
    in_parc = File(
        exists=True, argstr="%s", position=-2, desc="parcellation file"
    )
    out_file = File(
        argstr="%s",
        mandatory=True,
        position=-1,
        desc="output file connectivity csv file",
    )
    nthreads = traits.Int(
        argstr="-nthreads %d",
        desc="number of threads. if zero, the number" " of available cpus will be used",
        nohash=True,
    )
    in_weights = File(
        exists=True,
        argstr="-tck_weights_in %s",
        desc="specify a text scalar file containing the streamline weights",
    )
    scale_length=traits.Bool(
        argstr="-scale_length",
        desc="scale each contribution to the connectome edge by the length of the streamline"
    )
    stat_edge=traits.Enum(
        "sum",
        "mean",
        "min",
        "max",
        argstr="-stat_edge %s",
        desc="statistic for combining the values from all streamlines in an edge into a single scale value for that edge (options are: sum,mean,min,max;default=sum)"
    )
    symmetric=traits.Bool(
        argstr='-symmetric',
        desc='make matrices symmetric'
    )
    zero_diag=traits.Bool(
        argstr='-zero_diagonal',
        desc='set matrix diagonal to zero on output'
    )
    force = traits.Bool(
        argstr='-force',
        desc='overwrite existing output file'
    )

class MakeConnectomeOutputSpec(TraitedSpec):
    out_file = File(argstr="%s", desc="output connectome csv file")

class MakeConnectome(CommandLine):
    """
    mrtrix3's tck2connectome interface, defaults to zero diagonal and symmetric outputs.
    """
    _cmd="tck2connectome"
    input_spec = MakeConnectomeInputSpec
    output_spec = MakeConnectomeOutputSpec

    def _list_outputs(self):
        outputs=self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.out_file)
        return outputs