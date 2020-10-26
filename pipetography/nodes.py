# AUTOGENERATED! DO NOT EDIT! File to edit: 02_nodes.ipynb (unless otherwise specified).

__all__ = ['PreProcNodes', 'ACPCNodes', 'PostProcNodes']

# Internal Cell
import os
from pathlib import Path
from itertools import product

import pipetography.core as ppt
import pipetography.postprocessing as pptp

from nipype import IdentityInterface, Function
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.pipeline import Node, MapNode, Workflow
from nipype.interfaces.mrtrix3.utils import BrainMask, TensorMetrics, DWIExtract, MRMath, Generate5tt
from nipype.interfaces.mrtrix3.preprocess import MRDeGibbs, DWIBiasCorrect, ResponseSD
from nipype.interfaces.mrtrix3.reconst import FitTensor, EstimateFOD, ConstrainedSphericalDeconvolution
from nipype.interfaces import ants
from nipype.interfaces import fsl

# Cell
class PreProcNodes:
    """
    All nodes in DWI preprocessing pipeline. All inputs are set during `pipeline.create_nodes()` call.

    Inputs:
        - bids_dir (str)
        - bids_path_template (dict)
        - bids_ext (str)
        - RPE_design (str)
        - sub_list (List)
        - ses_list (List)
        - exclude_list (tuple)
    """
    def __init__(self, bids_dir, bids_path_template, bids_ext, RPE_design, sub_list, ses_list, exclude_list = [()]):
        # create sub-graphs for subjects and sessions combos
        all_sub_ses_combos = set(product(sub_list, ses_list))
        filtered_sub_ses_list = list(all_sub_ses_combos - set(exclude_list))
        sub_iter = [tup[0] for tup in filtered_sub_ses_list]
        ses_iter = [tup[1] for tup in filtered_sub_ses_list]
        self.subject_source = Node(IdentityInterface(fields=["subject_id", "session_id"]),
                                   iterables=[("subject_id", sub_iter), ("session_id", ses_iter)],
                                   synchronize=True,
                                   name = "sub_source")
        # reverse phase encoding design selection
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
        self.GradUpdate = Node(
            ppt.GradCheck(),
            name = 'alter_gradient'
        )
        self.ModGrad = Node(
            ppt.MRInfo(),
            name = 'modify_gradient'
        )
        self.UpdateMif = Node(
            ppt.Convert(),
            name =  'update_image'
        )
        self.NewMask =  Node(
                BrainMask(),
                name='recreate_mask'
        )
        self.biascorrect = Node(
            ppt.BiasCorrect(),
            name = 'dwibiascorrect',
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
            name = "ConvertRician",
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
        self.fslpreproc.inputs.export_grad=True
        self.fslpreproc.inputs.out_bfile='eddy_dwi.b'
        self.GradUpdate.inputs.export_grad=True
        self.GradUpdate.inputs.out_bfile='tmp.b'
        self.ModGrad.inputs.export_grad=True
        self.ModGrad.inputs.out_bfile='modified.b'
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
    Anatomy related and Freesurfer nodes. Mainly ACPC alignment of T1 and DWI and extraction of white matter mask.
    Inputs:
        - MNI_template: path to MNI template provided by FSL.
    """
    def __init__(self, MNI_template):
        ## removed get_fs_id
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
        ## removed reconall
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
        self.gen_5tt = Node(
            Generate5tt(),
            name='mrtrix_5ttgen',
        )
        self.convert2wm = Node(
            ppt.Convert(),
            name='5tt2wm',
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
        self.gen_5tt.inputs.algorithm = 'fsl'
        self.gen_5tt.inputs.out_file = 'mrtrix3_5tt.mif'
        self.convert2wm.inputs.coord = [3, 2]
        self.convert2wm.inputs.axes = [0, 1, 2]
        self.convert2wm.inputs.out_file = '5tt_wm.nii.gz'

# Cell

class PostProcNodes:
    """
    Inputs:
        atlas_dir (str): string path to folder containing all parcellations.
        atlas_list (list): list of parcellation names as saved in `atlas_dir`.
        atlas_template (dict): template directory for parcellation files
        data_dir (str): Path to directory containing "derivatives" and "cuda_tracking" output folders
        subj_template (dict): template directory for tck, dwi, T1, mask files
    """

    def __init__(self, atlas_dir, atlas_list, atlas_template, data_dir, subj_template):
        # Atlas input:
        self.atlas_source = Node(
            IdentityInterface(fields=["atlas_name"]),
            iterables=[("atlas_name", atlas_list)],
            name="atlas_source",
        )
        self.select_atlases = Node(
            SelectFiles(atlas_template),
            base_directory = atlas_dir,
            name = 'select_atlases'
        )
        # DWI input:
        self.subject_source = Node(
            IdentityInterface(fields=["subject_id", "session_id"]),
            name = 'subj_source'
        )
        self.select_files = Node(
            SelectFiles(subj_template),
            base_directory = data_dir,
            name = 'select_subjects'
        )
        self.linear_reg = Node(
            ants.Registration(),
            name = 'linear_registration'
        )
        self.nonlinear_reg = Node(
            ants.Registration(),
            name = 'nonlinear_registration'
        )
        self.round_atlas = Node(
            ppt.CheckNIZ(),
            name = 'round_parcellation'
        )
        self.response = Node(
            ResponseSD(),
            name = 'SDResponse'
        )
        self.fod = Node(
            ConstrainedSphericalDeconvolution(),
            name = 'dwiFOD'
        )
        self.sift2 = Node(
            pptp.tckSIFT2(),
            name = 'sift2_filtering'
        )
        self.connectome = Node(
            pptp.MakeConnectome(),
            name = 'weight_connectome'
        )
        self.distance = Node(
            pptp.MakeConnectome(),
            name = 'weight_distance'
        )
        self.datasink = Node(
            DataSink(
                base_directory=os.path.join(Path(data_dir), 'derivatives')
            ),
            name="datasink"
        )
        print('Data sink (output folder) is set to {}'.format(os.path.join(Path(data_dir), 'derivatives')))

    def set_inputs(self):
        # ANTS Registration
        self.linear_reg.inputs.output_transform_prefix = 'atlas_in_dwi_affine'
        self.linear_reg.inputs.dimension = 3
        self.linear_reg.inputs.collapse_output_transforms = True # -z flag
        self.linear_reg.inputs.transforms = ['Affine']
        self.linear_reg.inputs.transform_parameters = [(0.1,)]
        self.linear_reg.inputs.metric = ['MI']  # -metric
        self.linear_reg.inputs.metric_weight = [1]  # default
        self.linear_reg.inputs.radius_or_number_of_bins = [64]
        self.linear_reg.inputs.number_of_iterations = [[500, 200, 200, 100]]
        self.linear_reg.inputs.convergence_threshold = [1e-6]
        self.linear_reg.inputs.convergence_window_size = [10]
        self.linear_reg.inputs.smoothing_sigmas = [[4,2,1,0]]  # -s
        self.linear_reg.inputs.sigma_units = ['vox']
        self.linear_reg.inputs.shrink_factors = [[8,4,2,1]]  # -f
        self.linear_reg.inputs.use_histogram_matching = [True]  # -u
        self.linear_reg.inputs.output_warped_image = 'atlas_in_dwi_affine.nii.gz'
        self.nonlinear_reg.inputs.output_transform_prefix = 'atlas_in_dwi_syn'
        self.nonlinear_reg.inputs.dimension = 3  # -d
        self.nonlinear_reg.inputs.collapse_output_transforms = True  # -z flag
        self.nonlinear_reg.inputs.transforms = ['SyN']
        self.nonlinear_reg.inputs.transform_parameters=[(0.1,)]
        self.nonlinear_reg.inputs.metric = ['MI']
        self.nonlinear_reg.inputs.metric_weight = [1] #default
        self.nonlinear_reg.inputs.radius_or_number_of_bins = [64]
        self.nonlinear_reg.inputs.number_of_iterations = [[500,200,200,100]]  # -convergence
        self.nonlinear_reg.inputs.convergence_threshold = [1e-06]
        self.nonlinear_reg.inputs.convergence_window_size = [10]
        self.nonlinear_reg.inputs.smoothing_sigmas = [[4,2,1,0]]  # -s
        self.nonlinear_reg.inputs.sigma_units = ['vox']
        self.nonlinear_reg.inputs.shrink_factor = [[8,4,2,1]]  # -f
        self.nonlinear_reg.inputs.use_histogram_matching = [True]  # -u
        self.nonlinear_reg.inputs.output_warped_image = 'atlas_in_dwi_syn.nii.gz'
        self.round_atlas.inputs.args = '-round'
        self.round_atlas.inputs.out_file = 'nodes.mif'
        self.response.inputs.algorithm = 'dhollander'
        self.response.inputs.wm_file = 'wm.txt'
        self.response.inputs.gm_file = 'gm.txt'
        self.response.inputs.csf_file = 'csf.txt'
        self.fod.inputs.algorithm = 'msmt_csd'
        self.fod.inputs.wm_txt = 'wm.txt'
        self.fod.inputs.gm_txt = 'gm.txt'
        self.fod.inputs.gm_odf = 'gm.mif'
        self.fod.inputs.csf_txt = 'csf.txt'
        self.fod.inputs.csf_odf = 'csf.mif'
        self.sift2.inputs.fd_scale_gm = True
        self.sift2.inputs.out_file = 'sift2.txt'
        self.connectome.inputs.out_file = 'connectome.csv'
        self.connectome.inputs.symmetric = True
        self.connectome.inputs.zero_diag = True
        self.distance.inputs.scale_length = True
        self.distance.inputs.stat_edge = 'mean'
        self.distance.inputs.symmetric = True
        self.distance.inputts.zero_diag = True
        self.distance.inputs.out_file = 'distances.csv'