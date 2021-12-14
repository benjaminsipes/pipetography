# AUTOGENERATED! DO NOT EDIT! File to edit: 02_nodes.ipynb (unless otherwise specified).

__all__ = ['PreProcNodes', 'ACPCNodes', 'PostProcNodes']

# Internal Cell
import os
import bids

bids.config.set_option("extension_initial_dot", True)

from pathlib import Path
from itertools import product

import pipetography.core as ppt

from nipype import IdentityInterface, Function
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.pipeline import Node, MapNode, Workflow
from nipype.interfaces.mrtrix3.utils import (
    BrainMask,
    TensorMetrics,
    DWIExtract,
    MRMath,
)
from nipype.interfaces.mrtrix3.preprocess import MRDeGibbs, DWIBiasCorrect, ResponseSD
from nipype.interfaces.mrtrix3.reconst import (
    FitTensor,
    EstimateFOD,
    ConstrainedSphericalDeconvolution,
)
from nipype.interfaces import ants
from nipype.interfaces import fsl

# Cell
class PreProcNodes:
    """
    Initiate DWI preprocessing pipeline nodes. This doesn't connect the nodes into a pipeline.

    Inputs:
        - bids_dir (str) -
        - bids_path_template (dict) - template for file naming conventions
        - bids_ext (str) -
        - rpe_design (str) - This is necessary to initiate nodes for single DWI volume, or additional nodes for reverse volume.
        - mrtrix_nthreads (int)
        - img_resol (str)
        - sub_list (List)
        - ses_list (List)
        - exclude_list (tuple)
    """

    def __init__(
        self,
        bids_dir,
        bids_path_template,
        bids_ext,
        rpe_design,
        mrtrix_nthreads,
        img_resol,
        sub_list,
        ses_list,
        exclude_list=[()],
    ):
        # filtter & create sub-graphs for subjects and sessions combos
        sub_iter, ses_iter = ppt.filter_workflow(bids_dir, sub_list, ses_list, exclude_list)
        # Create BIDS nodes:
        BIDSFolders = [
            (
                "preprocessed/ses-%ssub-%s" % (session, subject),
                "sub-%s/ses-%s/preprocessed" % (subject, session),
            )
            for session in ses_list
            for subject in sub_list
        ]
        # IdentityInterface for file input:
        self.subject_source = Node(
            IdentityInterface(fields=["subject_id", "session_id"]),
            iterables=[("subject_id", sub_iter), ("session_id", ses_iter)],
            synchronize=True,
            name="SubjectDataSource",
        )
        self.subject_source.inputs.ext = bids_ext

        # reverse phase encoding design selection
        # If only one DWI volume:
        if rpe_design == "-rpe_none":
            # Gradient files input:
            self.sub_grad_files = Node(
                Function(
                    input_names=["sub_dwi", "ext"],
                    output_names=["fslgrad"],
                    function=ppt.get_sub_gradfiles,
                    ext=bids_ext,
                ),
                name="SubjectGradientSource",
            )
            self.sub_grad_files.inputs.ext = bids_ext
            # Reorient DWI to standard orientation for FSL:
            self.DWIReorient = Node(
                fsl.utils.Reorient2Std(
                    args = '-m mnitransformation.mat',
                    out_file = 'dwi_reorient.nii.gz'
                ),
                name = "DWIReorient"
            )
            # Convert from nifti to mrtrix3's mif format:
            self.mrconvert = Node(
                ppt.Convert(
                    out_file="raw_dwi.mif",
                    export_grad="raw_dwi.b",
                    nthreads=mrtrix_nthreads,
                ),
                name="Convert2Mif",
            )
        # If there are two DWI images with second volume being reverse direction:
        elif rpe_design == "-rpe_all":
            # Forward direction gradient file
            self.sub_grad_files1 = Node(
                Function(
                    input_names=["sub_dwi", "ext"],
                    output_names=["fslgrad"],
                    function=ppt.get_sub_gradfiles,
                    ext=bids_ext,
                ),
                name="SubjectGradientForward",
            )
            # Reverse direction gradient file
            self.sub_grad_files2 = Node(
                Function(
                    input_names=["sub_dwi", "ext"],
                    output_names=["fslgrad"],
                    function=ppt.get_sub_gradfiles,
                    ext=bids_ext,
                ),
                name="SubjectGradientReverse",
            )
            self.sub_grad_files1.inputs.ext = bids_ext
            self.sub_grad_files2.inputs.ext = bids_ext
            # Forward and reverses direction reorientation to FSL standard
            self.DWIReorientForward = Node(
                fsl.utils.Reorient2Std(
                    args = '-m forward_mni_transformation.mat',
                    out_file = 'dwi_reorient_forward.nii.gz'
                ),
                name = "DWIReorientForward",
            )
            self.DWIReorientReverse = Node(
                fsl.utils.Reorient2Std(
                    args = '-m reverse_mni_transformation.mat',
                    out_file = 'dwi_reorient_reverse.nii.gz'
                ),
                name = "DWIReorientReverse",
            )
            # Conversion from nifti to mif
            self.mrconvert1 = Node(
                ppt.Convert(
                    out_file="raw_dwi1.mif",
                    export_grad="raw_dwi1.b",
                    nthreads=mrtrix_nthreads,
                ),
                name="Convert2MifForward",
            )
            self.mrconvert2 = Node(
                ppt.Convert(
                    out_file="raw_dwi2.mif",
                    export_grad="raw_dwi2.b",
                    nthreads=mrtrix_nthreads,
                ),
                name="Convert2MifReverse",
            )
            # concatenate the two images and their gradient files.
            self.mrconcat = Node(ppt.MRCat(out_file="raw_dwi.mif"), name="concat_dwi",)
            self.gradcat = Node(ppt.GradCat(out_file="raw_dwi.b"), name="concat_grad",)

        self.select_files = Node(
            SelectFiles(bids_path_template, base_directory=bids_dir),
            name="SelectFiles",
        )

        self.get_metadata = Node(
            Function(
                input_names=["path", "bids_dir"],
                output_names=["ReadoutTime", "PE_DIR"],
                function=ppt.BIDS_metadata,
            ),
            name="GetMetaData",
        )
        self.get_metadata.inputs.bids_dir = bids_dir

        self.createMask = Node(
            BrainMask(out_file="b0_brain_mask.mif", nthreads=mrtrix_nthreads),
            name="Dwi2Mask",
        )

        self.GradCheck = Node(
            ppt.GradCheck(export_grad="corrected.b", nthreads=mrtrix_nthreads),
            name="GradientCheck",
        )

        self.NewGradMR = Node(
            ppt.Convert(out_file="corrected_dwi.mif", nthreads=mrtrix_nthreads),
            name="ConvertDWI2Mif",
        )

        self.denoise = Node(
            ppt.dwidenoise(
                out_file="denoised.mif", noise="noise_map.mif", nthreads=mrtrix_nthreads
            ),
            name="Denoise",
        )

        self.degibbs = Node(
            MRDeGibbs(out_file="unring.mif", nthreads=mrtrix_nthreads),
            name="RingingRemoval",
        )

        self.fslpreproc = Node(
            ppt.dwipreproc(
                out_file="preproc.mif",
                rpe_options=rpe_design,
                eddy_options='"--slm=linear --repol "',
                nthreads=mrtrix_nthreads,
                export_grad="eddy_dwi.b",
            ),
            name="DWIFSLPreproc",
        )

        self.GradUpdate = Node(
            ppt.GradCheck(export_grad="tmp.b"), name="AlteredGradient"
        )

        self.ModGrad = Node(
            ppt.MRInfo(export_grad="modified.b"), name="ModifyGradient"
        )

        self.UpdateMif = Node(ppt.Convert(), name="UpdateMif")

        self.NewMask = Node(BrainMask(), name="RecreateMask")

        self.biascorrect = Node(
            ppt.BiasCorrect(
                use_ants=True,
                out_file="dwi_bias.mif",
                bias="biasfield.mif",
                nthreads=mrtrix_nthreads,
            ),
            name="BiasCorrection",
        )

        self.grad_info = Node(
            ppt.MRInfo(export_grad="rician_tmp.b", nthreads=mrtrix_nthreads),
            name="NewGradient",
        )

        self.low_noise_map = Node(
            ppt.CheckNIZ(out_file="lownoisemap.mif", nthreads=mrtrix_nthreads),
            name="LowNoiseMap",
        )

        self.rician_noise = Node(
            ppt.RicianNoise(
                power=2,
                denoise=2,
                out_file="rician_removed_dwi.mif",
                nthreads=mrtrix_nthreads,
            ),
            name="RicianNoise",
        )

        self.check_rician = Node(
            ppt.CheckNIZ(out_file="rician_tmp.mif", nthreads=mrtrix_nthreads),
            name="NoiseComparison",
        )

        self.convert_rician = Node(
            ppt.Convert(out_file="rician_corrected_dwi.mif", nthreads=mrtrix_nthreads),
            name="ConvertRician",
        )
        self.dwi_mask = Node(BrainMask(out_file="dwi_mask.mif"), name="dwi2mask",)
        self.fit_tensor = Node(FitTensor(out_file="dti.mif"), name="dwi2tensor",)
        self.tensor_FA = Node(TensorMetrics(out_fa="fa.mif"), name="tensor2metrics",)
        self.wm_mask = Node(
            ppt.MRThreshold(opt_abs=0.5, out_file="wm.mif", nthreads=mrtrix_nthreads),
            name="mrthreshold",
        )
        self.norm_intensity = Node(
            ppt.DWINormalize(
                opt_intensity=1000,
                out_file="dwi_norm_intensity.mif",
                nthreads=mrtrix_nthreads,
            ),
            name="DWINormalise",
        )
        self.sub_b0extract = Node(
            DWIExtract(bzero=True, out_file="b0_volume.mif", nthreads=mrtrix_nthreads),
            name="ExtractB0Image",
        )
        self.sub_b0mean = Node(
            MRMath(
                operation="mean",
                axis=3,
                out_file="b0_dwi.mif",
                nthreads=mrtrix_nthreads,
            ),
            name="MeanB0Volume",
        )
        self.sub_b0mask = Node(
            BrainMask(out_file="dwi_norm_mask.mif", nthreads=mrtrix_nthreads),
            name="DWI2Mask",
        )
        self.sub_convert_dwi = Node(
            ppt.Convert(out_file="b0_dwi.nii.gz"), name="DWI2Nifti",
        )
        self.sub_convert_mask = Node(
            ppt.Convert(out_file="dwi_norm_mask.nii.gz"), name="Mask2Nifti",
        )
        self.sub_apply_mask = Node(
            fsl.ApplyMask(out_file="b0_dwi_brain.nii.gz"), name="ApplyMask",
        )
        self.mni_b0extract = Node(
            DWIExtract(
                bzero=True,
                out_file="dwi_space-acpc_res-{}_b0.mif".format(img_resol),
                nthreads=mrtrix_nthreads,
            ),
            name="MNIExtractB0Volume",
        )
        self.mni_b0mean = Node(
            MRMath(
                operation="mean",
                axis=3,
                out_file="dwi_space-acpc_res-{}_b0mean.mif".format(img_resol),
                nthreads=mrtrix_nthreads,
            ),
            name="MNIB0MeanVolume",
        )
        self.mni_b0mask = Node(
            BrainMask(
                out_file="dwi_space-acpc_res-{}_mask.mif".format(img_resol),
                nthreads=mrtrix_nthreads,
            ),
            name="MNIB0BrainMask",
        )
        self.mni_convert_dwi = Node(
            ppt.Convert(
                out_file="dwi_space-acpc_res-{}_b0mean.nii.gz".format(img_resol)
            ),
            name="MNIDWI2Nifti",
        )
        self.mni_convert_mask = Node(
            ppt.Convert(
                out_file="dwi_space-acpc_res-{}_seg-brain_mask.nii.gz".format(img_resol)
            ),
            name="MNIMask2Nifti",
        )
        self.mni_apply_mask = Node(
            fsl.ApplyMask(
                out_file="dwi_space-acpc_res-{}_seg-brain.nii.gz".format(img_resol)
            ),
            name="MNIApplyMask",
        )
        self.mni_dwi = Node(
            ppt.Convert(
                out_file="dwi_space-acpc_res-{}.nii.gz".format(img_resol),
                export_grad="dwi_space-acpc_res-{}.b".format(img_resol),
                export_fslgrad=(
                    "dwi_space-acpc_res-{}.bvecs".format(img_resol),
                    "dwi_space-acpc_res-{}.bvals".format(img_resol),
                ),
                export_json=True,
                nthreads=mrtrix_nthreads,
                out_json="dwi_space-acpc_res-{}.json".format(img_resol),
            ),
            name="MNI_Outputs",
        )

        self.datasink = Node(
            DataSink(
                base_directory=os.path.join(bids_dir, "derivatives", "pipetography")
            ),
            name="DataSink",
        )
        substitutions = [
            ("_subject_id_", "sub-"),
            ("_session_id_", "ses-"),
            *BIDSFolders,
        ]

        self.datasink.inputs.substitutions = substitutions
        print(
            "Data sink (output folder) is set to {}".format(
                os.path.join(bids_dir, "derivatives", "pipetography")
            )
        )

# Cell
class ACPCNodes:
    """
    T1 anatomy image related nodes. Mainly ACPC alignment of T1 and DWI and extraction of white matter mask.
    Inputs:
        - MNI_template: path to MNI template provided by FSL. By default uses the environment variable FSLDIR to locate the reference templates for ACPC alignment.
    """

    def __init__(self, MNI_template):
        self.T1Reorient = Node(
            fsl.utils.Reorient2Std(
                args = '-m mnitransformation.mat',
                out_file = 'T1_reoriented.nii.gz'
            ),
            name = 'T1Reorient'
        )
        self.reduceFOV = Node(
            fsl.utils.RobustFOV(
                out_transform="roi2full.mat", out_roi="robustfov.nii.gz"
            ),
            name="ReduceFOV",
        )
        self.xfminverse = Node(
            fsl.utils.ConvertXFM(out_file="full2roi.mat", invert_xfm=True),
            name="InverseTransformation",
        )
        self.flirt = Node(
            fsl.preprocess.FLIRT(
                reference=MNI_template,
                interp="spline",
                out_matrix_file="roi2std.mat",
                out_file="acpc_mni.nii.gz",
            ),
            name="FLIRT",
        )
        self.concatxfm = Node(
            fsl.utils.ConvertXFM(concat_xfm=True, out_file="full2std.mat"),
            name="ConcatTransform",
        )

        self.alignxfm = Node(
            ppt.fslaff2rigid(out_file="outputmatrix"), name="aff2rigid",
        )

        self.ACPC_warp = Node(
            fsl.preprocess.ApplyWarp(
                out_file="T1w_space-acpc.nii.gz",
                relwarp=True,
                output_type="NIFTI_GZ",
                interp="spline",
                ref_file=MNI_template,
            ),
            name="ACPCApplyWarp",
        )

        self.t1_bet = Node(
            fsl.preprocess.BET(mask=True, robust=True, out_file="acpc_t1_brain.nii.gz"),
            name="FSLBet",
        )

        self.epi_reg = Node(fsl.epi.EpiReg(out_base="dwi2acpc"), name="fsl_epireg",)

        self.acpc_xfm = Node(
            ppt.TransConvert(flirt=True, out_file="dwi2acpc_xfm.mat", force=True),
            name="ConvertTransformation",
        )

        self.apply_xfm = Node(
            ppt.MRTransform(out_file="dwi_acpc.mif"), name="MRTransform",
        )

        self.regrid = Node(
            ppt.MRRegrid(
                out_file="dwi_space-acpc_res-1mm.mif",
                regrid=MNI_template,
            ),
            name="Regrid",
        )

        self.gen_5tt = Node(
            ppt.Make5ttFSL(premasked=True, out_file="T1w_space-acpc_seg-5tt.mif"),
            name="Mrtrix5TTGen",
        )
        self.gmwmi = Node(ppt.gmwmi(out_file="gmwmi.nii.gz"), name="5tt2gmwmi")
        self.binarize_gmwmi = Node(
            ppt.MRThreshold(
                opt_abs=0.05, out_file="T1w_space-acpc_seg-gmwmi_mask.nii.gz"
            ),
            name="GMWMI",
        )
        self.convert2wm = Node(
            ppt.Convert(
                coord=[3, 2],
                axes=[0, 1, 2],
                out_file="T1w_space-acpc_seg-wm_mask.nii.gz",
            ),
            name="GetWMMask",
        )

# Cell
class PostProcNodes:
    """
    Inputs:
        BIDS_dir (str): Path to BIDS directory
        subj_template (dict): template directory for tck, dwi, T1, mask files
        sub_list (list): subjects IDs list generated from BIDS layout
        ses_list (list): sessions IDs listgenerated from BIDS layout
        skip_tuples (tuple): [('subject', 'session')] string pair to skip
    """

    def __init__(self, BIDS_dir, subj_template, sub_list, ses_list, skip_tuples):
        # filter & create sub-graphs for subjects and session combos:
        sub_iter, ses_iter = ppt.filter_workflow(BIDS_dir, sub_list, ses_list, skip_tuples)

        # Create BIDS output folder list for datasink
        BIDSFolders = [
            (
                "connectomes/ses-%ssub-%s" % (session, subject),
                "sub-%s/ses-%s/connectomes" % (subject, session),
            )
            for session in ses_list
            for subject in sub_list
        ]
        preproc_dir = os.path.join(
            BIDS_dir, "derivatives", "pipetography"
        )  # BIDS derivatives directory containing preprocessed outputs and streamline outputs

        # DWI input:
        self.subject_source = Node(
            IdentityInterface(fields=["subject_id", "session_id"]),
            iterables=[("subject_id", sub_iter), ("session_id", ses_iter)],
            synchronize=True,
            name="subj_source",
        )
        self.select_files = Node(
            SelectFiles(subj_template), base_directory=BIDS_dir, name="select_subjects"
        )
        self.linear_reg = Node(
            ants.Registration(
                output_transform_prefix="atlas_in_dwi_affine",
                dimension=3,
                collapse_output_transforms=True,
                transforms=["Affine"],
                transform_parameters=[(0.1,)],
                metric=["MI"],
                metric_weight=[1],
                radius_or_number_of_bins=[64],
                number_of_iterations=[[500, 200, 200, 100]],
                convergence_threshold=[1e-6],
                convergence_window_size=[10],
                smoothing_sigmas=[[4, 2, 1, 0]],
                sigma_units=["vox"],
                shrink_factors=[[8, 4, 2, 1]],
                use_histogram_matching=[True],
                output_warped_image="atlas_in_dwi_affine.nii.gz",
                interpolation="genericLabel",
            ),
            name="linear_registration",
        )
        self.nonlinear_reg = Node(
            ants.Registration(
                output_transform_prefix="atlas_in_dwi_syn",
                dimension=3,
                collapse_output_transforms=True,
                transforms=["SyN"],
                transform_parameters=[(0.1,)],
                metric=["MI"],
                metric_weight=[1],
                radius_or_number_of_bins=[64],
                number_of_iterations=[[500, 200, 200, 100]],
                convergence_threshold=[1e-06],
                convergence_window_size=[10],
                smoothing_sigmas=[[4, 2, 1, 0]],
                sigma_units=["vox"],
                shrink_factors=[[8, 4, 2, 1]],
                use_histogram_matching=[True],
                output_warped_image="atlas_in_dwi_syn.nii.gz",
                interpolation="genericLabel",
            ),
            name="nonlinear_registration",
        )
        self.response = Node(
            ResponseSD(
                algorithm="dhollander",
                wm_file="wm.txt",
                gm_file="gm.txt",
                csf_file="csf.txt",
            ),
            name="SDResponse",
        )
        self.fod = Node(
            ConstrainedSphericalDeconvolution(
                algorithm="msmt_csd",
                wm_txt="wm.txt",
                gm_txt="gm.txt",
                gm_odf="gm.mif",
                csf_txt="csf.txt",
                csf_odf="csf.mif",
            ),
            name="dwiFOD",
        )
        self.sift2 = Node(
            ppt.tckSIFT2(fd_scale_gm=True, out_file="sift2.txt"), name="sift2_filtering"
        )
        self.connectome = Node(
            ppt.MakeConnectome(
                out_file="connectome.csv", symmetric=True, zero_diag=True
            ),
            name="weight_connectome",
        )
        self.distance = Node(
            ppt.MakeConnectome(
                scale_length=True,
                stat_edge="mean",
                symmetric=True,
                zero_diag=True,
                out_file="distances.csv",
            ),
            name="weight_distance",
        )
        self.datasink = Node(DataSink(base_directory=preproc_dir), name="datasink")
        substitutions = [("_subject_id_", "sub-"), ("_session_id_", "ses-")]
        substitutions.extend(BIDSFolders)
        self.datasink.inputs.substitutions = substitutions
        self.datasink.inputs.regexp_substitutions = [
            (r"(_moving_image_.*\.\.)", ""),
            (r"(\.nii|\.gz)", ""),
        ]
        print("Data sink (output folder) is set to {}".format(preproc_dir))