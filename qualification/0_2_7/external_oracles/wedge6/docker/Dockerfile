FROM simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435

LABEL org.opencontainers.image.title="QF Solver Code_Aster headless oracle"
LABEL org.opencontainers.image.description="Code_Aster 18.1.0 one-process headless oracle with the image's pinned Spack view exposed"
LABEL org.opencontainers.image.base.name="simvia/code_aster:18.1.0"
LABEL org.opencontainers.image.base.digest="sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"

# The base image contains mpi4py and NumPy in the simvia Spack view, but the
# stock profile does not expose that view to Python or the dynamic linker.
ENV CODE_ASTER_VIEW=/opt/spack/var/spack/environments/simvia_env/.spack-env/._view/nmzlyspcgasoeembakyuu32kyediheiv
ENV PYTHONPATH=/opt/spack/var/spack/environments/simvia_env/.spack-env/._view/nmzlyspcgasoeembakyuu32kyediheiv/lib/python3.11/site-packages
ENV LD_LIBRARY_PATH=/opt/spack/var/spack/environments/simvia_env/.spack-env/._view/nmzlyspcgasoeembakyuu32kyediheiv/lib:/opt/spack/var/spack/environments/simvia_env/.spack-env/._view/nmzlyspcgasoeembakyuu32kyediheiv/lib64
ENV CODE_ASTER_PREFIX=/opt/spack/opt/spack/linux-zen/code-aster-18.1.0-owafurl325k3dbxls3s645zyfmvakxsg

ENTRYPOINT ["/opt/spack/opt/spack/linux-zen/code-aster-18.1.0-owafurl325k3dbxls3s645zyfmvakxsg/bin/run_aster"]
