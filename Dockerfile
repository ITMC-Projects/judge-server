# Public VNOJ judge image; the previous vnoj/judge-tier1 repository is unavailable.
ARG BASE_IMAGE=vnoj/judge-tiervnoj@sha256:8c98a2be3bd755ba9532d069316c5190bcf86f4ac742001b168f783e8268b548
FROM ${BASE_IMAGE}

USER root
WORKDIR /judge
ENV DMOJ_TARGET_ARCH=x86-64 DMOJ_PARALLEL=4
# Replace upstream source, including old compiled extensions, with this checkout.
RUN rm -rf /judge && mkdir /judge
COPY . /judge/
RUN /env/bin/pip3 install --no-build-isolation --no-deps -e . && \
    sed -i 's/\r$//' /judge/.docker/local-entry && \
    chmod 755 /judge/.docker/local-entry
ENTRYPOINT ["/usr/bin/tini", "--", "/judge/.docker/local-entry"]
CMD ["run", "vnoj_bridged", "-p", "9999", "-c", "/judge/.docker/judge.yml"]
