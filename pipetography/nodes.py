# AUTOGENERATED! DO NOT EDIT! File to edit: 02_nodes.ipynb (unless otherwise specified).

__all__ = ['PreProcNodes', 'ACPCNodes']

# Internal Cell
import os
from pathlib import Path

import pipetography.core as ppt

from nipype import IdentityInterface, Function
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.pipeline import Node, MapNode, Workflow
from nipype.interfaces.freesurfer.preprocess import ReconAll
from nipype.interfaces.mrtrix3.utils import BrainMask, TensorMetrics, DWIExtract, MRMath
from nipype.interfaces.mrtrix3.preprocess import MRDeGibbs, DWIBiasCorrect
from nipype.interfaces.mrtrix3.reconst import FitTensor
from nipype.interfaces import ants
from nipype.interfaces import fsl

# Cell
class PreProcNodes:
    """
    All nodes in preprocessing pipeline
    """
    def __init__(self, bids_dir, bids_path_template, bids_ext, sub_list, RPE_design):
        self.subject_source = Node(IdentityInterface(fields=["subject_id", "ext"]), name = "sub_source")
        self.subject_source.iterables=[("subject_id", sub_list)]
        if RPE_design == '-rpe_none':
            self.sub_grad_files = Node(
                Function(input_names=['sub_dwi', 'ext'],
                    output_names=["fslgrad"],
                    function=ppt.get_sub_gradfiles
                ),
                name = 'sub_grad_files',
            )
            self.mrconvert = Node(
                ppt.Convert(),
                name='mrtrix_image',
            )
        elif RPE_design == '-rpe_all':
            self.sub_grad_files1 = Node(
                Function(
                    input_names=["sub_dwi", "ext"],
                    output_names=["fslgrad"],
                    function=ppt.get_sub_gradfiles
                ),
                name = "sub_grad_files1",
            )
            self.sub_grad_files2 = Node(
                Function(
                    input_names=["sub_dwi", "ext"],
                    output_names=["fslgrad"],
                    function=ppt.get_sub_gradfiles
                ),
                name = "sub_grad_files2",
            )
            self.mrconvert1 = Node(
                ppt.Convert(),
                name='mrtrix_image1',
            )
            self.mrconvert2 = Node(
                ppt.Convert(),
                name='mrtrix_image2',
            )
            # concatenate the two images and their gradient files.
            self.mrconcat = Node(
                ppt.MRCat(),
                name='concat_dwi',
            )
            self.gradcat = Node(
                ppt.GradCat(),
                name='concat_grad',
            )
        self.select_files = Node(
            SelectFiles(bids_path_template, base_directory=bids_dir),
            name='select_files'
        )
        self.get_metadata = Node(
            Function(
                input_names=['path', 'bids_dir'],
                output_names=['ReadoutTime', 'PE_DIR'],
                function=ppt.BIDS_metadata
            ),
            name='get_metadata',
        )
        self.createMask = Node(
            BrainMask(),
            name='raw_dwi2mask',
        )
        self.GradCheck = Node(
            ppt.GradCheck(),
            name='dwigradcheck',
        )
        self.NewGradMR = Node(
            ppt.Convert(),
            name='mrconvert',
        )
        self.denoise = Node(
            ppt.dwidenoise(),
            name='denoise',
        )
        self.degibbs = Node(
            MRDeGibbs(),
            name='ringing_removal',
        )
        self.fslpreproc = Node(
            ppt.dwipreproc(),
            name = "dwifslpreproc",
        )
        self.biascorrect = Node(
            ppt.BiasCorrect(),
            name = 'dwibiascorret',
        )
        self.grad_info = Node(
            ppt.MRInfo(),
            name = 'NewGradient',
        )
        self.low_noise_map = Node(
            ppt.CheckNIZ(),
            name = 'LowNoiseMap',
        )
        self.rician_noise = Node(
            ppt.RicianNoise(),
            name = 'RicianNoise',
        )
        self.check_rician = Node(
            ppt.CheckNIZ(),
            name = 'NoiseComparison',
        )
        self.convert_rician = Node(
            ppt.Convert(),
            name = "ConvnertRician",
        )
        self.dwi_mask = Node(
            BrainMask(),
            name='dwi2mask',
        )
        self.fit_tensor = Node(
            FitTensor(),
            name='dwi2tensor',
        )
        self.tensor_FA = Node(
            TensorMetrics(),
            name='tensor2metrics',
        )
        self.wm_mask = Node(
            ppt.MRThreshold(),
            name = 'mrthreshold',
        )
        self.norm_intensity = Node(
            ppt.DWINormalize(),
            name='dwinormalise',
        )
        self.sub_b0extract = Node(
            DWIExtract(),
            name='sub_b0extract',
        )
        self.sub_b0mean = Node(
            MRMath(),
            name='sub_mrmath_mean',
        )
        self.sub_b0mask = Node(
            BrainMask(),
            name='sub_dwi2mask',
        )
        self.sub_convert_dwi = Node(
            ppt.Convert(),
            name="sub_dwi2nii",
        )
        self.sub_convert_mask = Node(
            ppt.Convert(),
            name="sub_mask2nii",
        )
        self.sub_apply_mask = Node(
            fsl.ApplyMask(),
            name='sub_ApplyMask',
        )
        self.mni_b0extract = Node(
            DWIExtract(),
            name='mni_b0extract',
        )
        self.mni_b0mean = Node(
            MRMath(),
            name='mni_mrmath_mean',
        )
        self.mni_b0mask = Node(
            BrainMask(),
            name='mni_dwi2mask',
        )
        self.mni_convert_dwi = Node(
            ppt.Convert(),
            name='mni_dwi2nii',
        )
        self.mni_convert_mask  = Node(
            ppt.Convert(),
            name='mni_mask2nii',
        )
        self.mni_apply_mask = Node(
            fsl.ApplyMask(),
            name='mni_ApplyMask',
        )
        self.mni_dwi = Node(
            ppt.Convert(),
            name='MNI_Outputs',
        )

        self.datasink = Node(
            DataSink(
                base_directory=os.path.join(Path(bids_dir).parent, 'derivatives')
            ),
            name="datasink"
        )
        print('Data sink (output folder) is set to {}'.format(os.path.join(Path(bids_dir).parent, 'derivatives')))

    def set_inputs(self, bids_dir, bids_ext, RPE_design, mrtrix_nthreads):
        self.subject_source.inputs.ext=bids_ext
        if RPE_design == '-rpe_none':
            self.sub_grad_files.inputs.ext = bids_ext
            self.mrconvert.inputs.out_file='raw_dwi.mif'
            self.mrconvert.inputs.export_grad=True
            self.mrconvert.inputs.out_bfile='raw_dwi.b'
            self.mrconvert.force=True
            self.mrconvert.quiet=True
            self.mrconvert.inputs.nthreads=mrtrix_nthreads
        elif RPE_design == '-rpe_all':
            self.sub_grad_files1.inputs.ext = bids_ext
            self.sub_grad_files2.inputs.ext = bids_ext
            self.mrconvert1.inputs.out_file='raw_dwi1.mif'
            self.mrconvert1.inputs.export_grad=True
            self.mrconvert1.inputs.out_bfile='raw_dwi1.b'
            self.mrconvert1.inputs.force=True
            self.mrconvert1.inputs.quiet=True
            self.mrconvert1.inputs.nthreads=mrtrix_nthreads
            self.mrconvert2.inputs.out_file='raw_dwi2.mif'
            self.mrconvert2.inputs.export_grad=True
            self.mrconvert2.inputs.out_bfile='raw_dwi2.b'
            self.mrconvert2.inputs.force=True
            self.mrconvert2.inputs.quiet=True
            self.mrconvert2.inputs.nthreads=mrtrix_nthreads
            self.mrconcat.inputs.out_file = 'raw_dwi.mif'
            self.gradcat.inputs.out_file = 'raw_dwi.b'
        self.createMask.inputs.out_file='b0_brain_mask.mif'
        self.createMask.inputs.nthreads=mrtrix_nthreads
        self.GradCheck.inputs.export_grad=True
        self.GradCheck.inputs.out_bfile='corrected.b'
        self.GradCheck.inputs.force=True
        self.GradCheck.inputs.quiet=True
        self.GradCheck.inputs.nthreads=mrtrix_nthreads
        self.NewGradMR.inputs.out_file='corrected_dwi.mif'
        self.NewGradMR.inputs.force=True
        self.NewGradMR.inputs.quiet=True
        self.NewGradMR.inputs.nthreads=mrtrix_nthreads
        self.denoise.inputs.out_file='denoised.mif'
        self.denoise.inputs.noise = 'noise_map.mif'
        self.denoise.inputs.force=True
        self.denoise.inputs.quiet=True
        self.denoise.inputs.nthreads=mrtrix_nthreads
        self.degibbs.inputs.out_file='unring.mif'
        self.get_metadata.inputs.bids_dir=bids_dir
        self.fslpreproc.inputs.out_file='preproc.mif'
        self.fslpreproc.inputs.rpe_options=RPE_design
        self.fslpreproc.inputs.eddy_options='"--slm=linear --repol "'
        self.fslpreproc.inputs.force=True
        self.fslpreproc.inputs.quiet=True
        self.fslpreproc.inputs.nthreads=mrtrix_nthreads
        self.biascorrect.inputs.use_ants=True
        self.biascorrect.inputs.out_file='dwi_bias.mif'
        self.biascorrect.inputs.bias='biasfield.mif'
        self.grad_info.inputs.export_grad=True
        self.grad_info.inputs.out_bfile = 'rician_tmp.b'
        self.grad_info.inputs.force=True
        self.grad_info.inputs.quiet=True
        self.grad_info.inputs.nthreads = mrtrix_nthreads
        self.low_noise_map.inputs.out_file = 'lownoisemap.mif'
        self.low_noise_map.inputs.force = True
        self.low_noise_map.inputs.quiet = True
        self.low_noise_map.inputs.nthreads = mrtrix_nthreads
        self.rician_noise.inputs.power = 2
        self.rician_noise.inputs.denoise = 2
        self.rician_noise.inputs.out_file = 'rician_removed_dwi.mif'
        self.rician_noise.inputs.force=True
        self.rician_noise.inputs.quiet=True
        self.rician_noise.inputs.nthreads=mrtrix_nthreads
        self.check_rician.inputs.out_file = 'rician_tmp.mif'
        self.check_rician.inputs.force = True
        self.check_rician.inputs.nthreads = mrtrix_nthreads
        self.convert_rician.inputs.out_file = 'rician_corrected_dwi.mif'
        self.convert_rician.inputs.force = True
        self.convert_rician.inputs.nthreads = mrtrix_nthreads
        self.wm_mask.inputs.opt_abs = 0.5
        self.wm_mask.inputs.force = True
        self.wm_mask.inputs.quiet = True
        self.wm_mask.inputs.out_file = 'wm.mif'
        self.wm_mask.inputs.nthreads = mrtrix_nthreads
        self.norm_intensity.inputs.opt_intensity = 1000
        self.norm_intensity.inputs.force = True
        self.norm_intensity.inputs.quiet = True
        self.norm_intensity.inputs.out_file = 'dwi_norm_intensity.mif'
        self.norm_intensity.inputs.nthreads = mrtrix_nthreads
        self.dwi_mask.inputs.out_file = 'dwi_mask.mif'
        self.fit_tensor.inputs.out_file = 'dti.mif'
        self.tensor_FA.inputs.out_fa = 'fa.mif'
        self.sub_b0extract.inputs.bzero = True
        self.sub_b0extract.inputs.out_file = 'b0_volume.mif'
        self.sub_b0extract.inputs.nthreads = mrtrix_nthreads
        self.sub_b0mean.inputs.operation = 'mean'
        self.sub_b0mean.inputs.axis = 3
        self.sub_b0mean.inputs.out_file = 'b0_dwi.mif'
        self.sub_b0mean.inputs.nthreads = mrtrix_nthreads
        self.sub_b0mask.inputs.out_file = 'dwi_norm_mask.mif'
        self.sub_convert_dwi.inputs.out_file = 'b0_dwi.nii.gz'
        self.sub_convert_dwi.inputs.force = True
        self.sub_convert_mask.inputs.force = True
        self.sub_convert_mask.inputs.out_file = 'dwi_norm_mask.nii.gz'
        self.sub_apply_mask.inputs.out_file = 'b0_dwi_brain.nii.gz'
        self.mni_b0extract.inputs.bzero = True
        self.mni_b0extract.inputs.out_file = 'dwi_acpc_1mm_b0.mif'
        self.mni_b0extract.inputs.nthreads = mrtrix_nthreads
        self.mni_b0mean.inputs.operation = 'mean'
        self.mni_b0mean.inputs.axis = 3
        self.mni_b0mean.inputs.out_file = 'dwi_acpc_1mm_b0mean.mif'
        self.mni_b0mean.inputs.nthreads = mrtrix_nthreads
        self.mni_b0mask.inputs.out_file = 'dwi_acpc_1mm_mask.mif'
        self.mni_convert_dwi.inputs.out_file = 'dwi_acpc_1mm_b0mean.nii.gz'
        self.mni_convert_mask.inputs.out_file = 'dwi_acpc_1mm_mask.nii.gz'
        self.mni_convert_dwi.inputs.force = True
        self.mni_convert_mask.inputs.force = True
        self.mni_apply_mask.inputs.out_file = 'dwi_acpc_1mm_brain.nii.gz'
        self.mni_dwi.inputs.out_file = 'dwi_acpc_1mm.nii.gz'
        self.mni_dwi.inputs.export_grad = True
        self.mni_dwi.inputs.export_fslgrad = True
        self.mni_dwi.inputs.export_json = True
        self.mni_dwi.inputs.force = True
        self.mni_dwi.inputs.nthreads = mrtrix_nthreads
        self.mni_dwi.inputs.out_bfile = 'dwi_acpc_1mm.b'
        self.mni_dwi.inputs.out_fslgrad = ('dwi_acpc.bvecs', 'dwi_acpc.bvals')
        self.mni_dwi.inputs.out_json = 'dwi_acpc_1mm.json'


# Cell
class ACPCNodes:
    """
    Freesurfer recon-all nodes
    """
    def __init__(self, MNI_template):
        self.get_fs_id = Node(
            Function(
                input_names=['anat_files'],
                output_names=['fs_id_list'],
                function=ppt.anat2id
            ),
            name='freesurfer_sub_id',
        )
        self.reduceFOV = Node(
            fsl.utils.RobustFOV(),
            name="reduce_FOV",
        )
        self.xfminverse = Node(
            fsl.utils.ConvertXFM(),
            name="transform_inverse",
        )
        self.flirt = Node(
            fsl.preprocess.FLIRT(),
            name="FLIRT",
        )
        self.concatxfm = Node(
            fsl.utils.ConvertXFM(),
            name="concat_transform",
        )
        self.alignxfm = Node(
            ppt.fslaff2rigid(),
            name='aff2rigid',
        )
        self.ACPC_warp = Node(
            fsl.preprocess.ApplyWarp(),
            name='apply_warp',
        )
        self.reconall = Node(
            ReconAll(),
            name='FSrecon',
        )
        self.t1_bet = Node(
            fsl.preprocess.BET(),
            name='fsl_bet',
        )
        self.epi_reg = Node(
            fsl.epi.EpiReg(),
            name='fsl_epireg',
        )
        self.acpc_xfm = Node(
            ppt.TransConvert(),
            name='transformconvert',
        )
        self.apply_xfm = Node(
            ppt.MRTransform(),
            name='mrtransform',
        )
        self.regrid = Node(
            ppt.MRRegrid(),
            name = 'mrgrid',
        )

    def set_inputs(self, bids_dir, MNI_template):
        self.reduceFOV.inputs.out_transform='roi2full.mat'
        self.reduceFOV.inputs.out_roi='robustfov.nii.gz'
        self.flirt.inputs.reference=MNI_template
        self.flirt.inputs.interp='spline'
        self.flirt.inputs.out_matrix_file='roi2std.mat'
        self.flirt.inputs.out_file='acpc_mni.nii.gz'
        self.xfminverse.inputs.out_file='full2roi.mat'
        self.xfminverse.inputs.invert_xfm=True
        self.concatxfm.inputs.concat_xfm=True
        self.concatxfm.inputs.out_file='full2std.mat'
        self.alignxfm.inputs.out_file='outputmatrix'
        self.ACPC_warp.inputs.out_file='acpc_t1.nii'
        self.ACPC_warp.inputs.relwarp=True
        self.ACPC_warp.inputs.output_type='NIFTI'
        self.ACPC_warp.inputs.interp='spline'
        self.ACPC_warp.inputs.ref_file=MNI_template
        self.reconall.inputs.parallel=False
        self.reconall.inputs.hippocampal_subfields_T1 = True
        self.reconall.inputs.directive='all'
        if not os.path.exists(os.path.join(Path(bids_dir).parent, 'derivatives', 'freesurfer')):
            print('No freesurfer subject folder (output folder) found, creating it at {}'.format(
                os.path.join(Path(bids_dir).parent, 'derivatives', 'freesurfer'))
                 )
            os.makedirs(os.path.join(Path(bids_dir).parent, 'derivatives', 'freesurfer'))
        elif os.path.exists(os.path.join(Path(bids_dir).parent, 'derivatives', 'freesurfer')):
            print('Freesurfer output at {}'.format(os.path.join(Path(bids_dir).parent, 'derivatives', 'freesurfer')))
        self.reconall.inputs.subjects_dir = os.path.join(
            Path(bids_dir).parent, 'derivatives', 'freesurfer'
        )
        self.t1_bet.inputs.mask = True
        self.t1_bet.inputs.robust = True
        self.t1_bet.inputs.out_file = 'acpc_t1_brain.nii.gz'
        self.epi_reg.inputs.out_base = 'dwi2acpc'
        self.acpc_xfm.inputs.flirt = True
        self.acpc_xfm.inputs.out_file = 'dwi2acpc_xfm.mat'
        self.acpc_xfm.inputs.force = True
        self.apply_xfm.inputs.out_file = 'dwi_acpc.mif'
        self.regrid.inputs.out_file = 'dwi_acpc_1mm.mif'
        self.regrid.inputs.regrid = MNI_template