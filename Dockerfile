ARG BASE_IMAGE=vnoj/judge-tier1@sha256:ab9406869defe9e3cebb6cea12b91826982d82afb5d1636ba77ffb282af9785f
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
