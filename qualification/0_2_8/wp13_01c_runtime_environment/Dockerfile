FROM mambaorg/micromamba:2.5.0

COPY --chown=$MAMBA_USER:$MAMBA_USER qualification/0_2_8/wp13_01c_runtime_environment/environment.yml /tmp/environment.yml
RUN micromamba create --yes --name qf-wp13-01c-petsc --file /tmp/environment.yml \
    && micromamba clean --all --yes

ENV ENV_NAME=qf-wp13-01c-petsc
