rm -rf *.rpm
fedpkg --release f39 srpm
mock -r fedora-39-aarch64 --enable-network --resultdir . *.rpm