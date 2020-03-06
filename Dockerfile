# Your version: 0.6.0 Latest version: 0.6.0
# Generated by Neurodocker version 0.6.0
# Timestamp: 2020-03-05 23:25:04 UTC
#
# Thank you for using Neurodocker. If you discover any issues
# or ways to improve this software, please submit an issue or
# pull request on our GitHub repository:
#
#     https://github.com/kaczmarj/neurodocker

FROM neurodebian

ARG DEBIAN_FRONTEND="noninteractive"

ENV LANG="en_US.UTF-8" \
    LC_ALL="en_US.UTF-8" \
    ND_ENTRYPOINT="/neurodocker/startup.sh"
RUN export ND_ENTRYPOINT="/neurodocker/startup.sh" \
    && apt-get update -qq \
    && apt-get install -y -q --no-install-recommends \
           apt-utils \
           bzip2 \
           ca-certificates \
           curl \
           locales \
           unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales \
    && update-locale LANG="en_US.UTF-8" \
    && chmod 777 /opt && chmod a+s /opt \
    && mkdir -p /neurodocker \
    && if [ ! -f "$ND_ENTRYPOINT" ]; then \
         echo '#!/usr/bin/env bash' >> "$ND_ENTRYPOINT" \
    &&   echo 'set -e' >> "$ND_ENTRYPOINT" \
    &&   echo 'export USER="${USER:=`whoami`}"' >> "$ND_ENTRYPOINT" \
    &&   echo 'if [ -n "$1" ]; then "$@"; else /usr/bin/env bash; fi' >> "$ND_ENTRYPOINT"; \
    fi \
    && chmod -R 777 /neurodocker && chmod a+s /neurodocker

ENTRYPOINT ["/neurodocker/startup.sh"]

ENV ANTSPATH="/opt/ants-2.3.1" \
    PATH="/opt/ants-2.3.1:$PATH"
RUN echo "Downloading ANTs ..." \
    && mkdir -p /opt/ants-2.3.1 \
    && curl -fsSL --retry 5 https://dl.dropbox.com/s/1xfhydsf4t4qoxg/ants-Linux-centos6_x86_64-v2.3.1.tar.gz \
    | tar -xz -C /opt/ants-2.3.1 --strip-components 1

ENV FSLDIR="/opt/fsl-6.0.1" \
    PATH="/opt/fsl-6.0.1/bin:$PATH"
RUN apt-get update -qq \
    && apt-get install -y -q --no-install-recommends \
           bc \
           dc \
           file \
           libfontconfig1 \
           libfreetype6 \
           libgl1-mesa-dev \
           libgl1-mesa-dri \
           libglu1-mesa-dev \
           libgomp1 \
           libice6 \
           libxcursor1 \
           libxft2 \
           libxinerama1 \
           libxrandr2 \
           libxrender1 \
           libxt6 \
           sudo \
           wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && echo "Downloading FSL ..." \
    && mkdir -p /opt/fsl-6.0.1 \
    && curl -fsSL --retry 5 https://fsl.fmrib.ox.ac.uk/fsldownloads/fsl-6.0.1-centos6_64.tar.gz \
    | tar -xz -C /opt/fsl-6.0.1 --strip-components 1 \
    && sed -i '$iecho Some packages in this Docker container are non-free' $ND_ENTRYPOINT \
    && sed -i '$iecho If you are considering commercial use of this container, please consult the relevant license:' $ND_ENTRYPOINT \
    && sed -i '$iecho https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Licence' $ND_ENTRYPOINT \
    && sed -i '$isource $FSLDIR/etc/fslconf/fsl.sh' $ND_ENTRYPOINT \
    && echo "Installing FSL conda environment ..." \
    && bash /opt/fsl-6.0.1/etc/fslconf/fslpython_install.sh -f /opt/fsl-6.0.1 \
    && echo "Downgrading deprecation module per https://github.com/kaczmarj/neurodocker/issues/271#issuecomment-514523420" \
    && /opt/fsl-6.0.1/fslpython/bin/conda install -n fslpython -c conda-forge -y deprecation==1.* \
    && echo "Removing bundled with FSLeyes libz likely incompatible with the one from OS" \
    && rm -f /opt/fsl-6.0.1/bin/FSLeyes/libz.so.1

ENV PATH="/opt/mrtrix3-3.0_RC3/bin:$PATH"
RUN echo "Downloading MRtrix3 ..." \
    && mkdir -p /opt/mrtrix3-3.0_RC3 \
    && curl -fsSL --retry 5 https://dl.dropbox.com/s/2oh339ehcxcf8xf/mrtrix3-3.0_RC3-Linux-centos6.9-x86_64.tar.gz \
    | tar -xz -C /opt/mrtrix3-3.0_RC3 --strip-components 1

RUN apt-get update -qq \
    && apt-get install -y -q --no-install-recommends \
           git \
           ssh \
           tar \
           gzip \
           ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV CONDA_DIR="/opt/miniconda-latest" \
    PATH="/opt/miniconda-latest/bin:$PATH"
RUN export PATH="/opt/miniconda-latest/bin:$PATH" \
    && echo "Downloading Miniconda installer ..." \
    && conda_installer="/tmp/miniconda.sh" \
    && curl -fsSL --retry 5 -o "$conda_installer" https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash "$conda_installer" -b -p /opt/miniconda-latest \
    && rm -f "$conda_installer" \
    && conda update -yq -nbase conda \
    && conda config --system --prepend channels conda-forge \
    && conda config --system --set auto_update_conda false \
    && conda config --system --set show_channel_urls true \
    && sync && conda clean --all && sync \
    && conda create -y -q --name tracts \
    && conda install -y -q --name tracts \
           "python=3.7.3" \
           "dipy" \
           "nibabel" \
           "nipype" \
           "matplotlib" \
           "pytest" \
    && sync && conda clean --all && sync \
    && bash -c "source activate tracts \
    &&   pip install --no-cache-dir  \
             "pybids" \
             "fastcore==0.1.11"" \
    && rm -rf ~/.cache/pip/* \
    && sync

RUN echo '{ \
    \n  "pkg_manager": "apt", \
    \n  "instructions": [ \
    \n    [ \
    \n      "base", \
    \n      "neurodebian" \
    \n    ], \
    \n    [ \
    \n      "ants", \
    \n      { \
    \n        "version": "2.3.1" \
    \n      } \
    \n    ], \
    \n    [ \
    \n      "fsl", \
    \n      { \
    \n        "version": "6.0.1" \
    \n      } \
    \n    ], \
    \n    [ \
    \n      "mrtrix3", \
    \n      { \
    \n        "version": "3.0_RC3" \
    \n      } \
    \n    ], \
    \n    [ \
    \n      "install", \
    \n      [ \
    \n        "git", \
    \n        "ssh", \
    \n        "tar", \
    \n        "gzip", \
    \n        "ca-certificates" \
    \n      ] \
    \n    ], \
    \n    [ \
    \n      "miniconda", \
    \n      { \
    \n        "create_env": "tracts", \
    \n        "conda_install": [ \
    \n          "python=3.7.3", \
    \n          "dipy", \
    \n          "nibabel", \
    \n          "nipype", \
    \n          "matplotlib", \
    \n          "pytest" \
    \n        ], \
    \n        "pip_install": [ \
    \n          "pybids", \
    \n          "fastcore==0.1.11" \
    \n        ] \
    \n      } \
    \n    ] \
    \n  ] \
    \n}' > /neurodocker/neurodocker_specs.json
    
