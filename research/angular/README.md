# Angular

## Setup

### Installation of Node

Current LTS is 18.13.0

curl -fsSL https://fnm.vercel.app/install | bash
source ~/.bashrc
fnm list-remote
fnm install v18.13.0
node --version

### Install Angular CLI

npm install -g npm@latest
npm install -global @angular/cli@latest

### Check

node --version
ng version

### Create project

ng new learn1

### Serve project (host on a port)

cd to_the_project
ng serve

## Create another component

ng generate component {nav/bla}


there are several others

ng generate --help

## Future modules to add

enable routing
ng add @angular/material

## add Bootstrap

npm install --save bootstrap

including it into angular

angular.json
```json
            "styles": [
              "src/styles.css",
              "node_modules/bootstrap/dist/css/bootstrap.rtl.css"
            ],
```

restart the serve to load and it should be included in the code going to the client