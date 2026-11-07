# vLLM serving image.
#
# On the PC the official image is imported straight into k3s, so this file is for
# documentation and for machines that have a registry:
#
#   docker pull vllm/vllm-openai:v0.28.0
#   docker save vllm/vllm-openai:v0.28.0 | sudo k3s ctr images import -
#
# The LoRA adapter folder is mounted at runtime (see k8s/vllm-deployment.yaml).

FROM vllm/vllm-openai:v0.28.0

# Folder for the weekly LoRA adapters.
RUN mkdir -p /adapters
VOLUME ["/adapters"]

# The base image allows only some driver versions. Turn off that check so a newer
# host driver can start the container.
ENV NVIDIA_DISABLE_REQUIRE=true

# The entrypoint comes from the base image: ["vllm", "serve"]
