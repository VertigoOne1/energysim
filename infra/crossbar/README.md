## Crossbar

docker pull crossbario/crossbar

docker run -v  ${PWD}/config/node:/node -u 0 --rm --name=crossbar -it -p 8080:8080 crossbario/crossbar