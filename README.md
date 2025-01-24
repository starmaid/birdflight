# BIRDFLIGHT

![](./docs/me_1.png)

This program is made to turn videos of birds into layered flight trail images.

## Try it out

The site is currently hosted on my personal server. Message me privately for the domain.

### Prior Art

![](./docs/XaviBou_12.jpg)

[Xavi Bou's ornithographies](https://xavibou.com/ornithographies/) are the classic still images. These are hand-crafted in photoshop from hundreds of stills, shot usually with a high-speed camera. He also seems to do movies as well.

![](./docs/dennis-1.gif)

[Dennis Hlynsky](https://www.thisiscolossal.com/2014/01/amazing-video-clips-visually-isolate-the-flight-paths-of-birds/) makes videos where a certain number of previous frames are visible, and fade out. A cool thing here is he overlays audio recorded from the location.


## Building and Hosting

First you will want to download the code to your computer. You can clone the latest code, or you can go to the [releases page](https://github.com/starmaid/birdflight/releases) to see stable versions. You can download the zip file from there, and unzip it.

You will need an install of [Docker](https://docs.docker.com/desktop/) on your system. If you are running a server, you can use the docker engine.

From there, you can open the command line inside the folder you downloaded and unzipped, and run this command:

```
docker compose up
```

This will build the container and start it. The server will appear on [http://127.0.0.1:5050/](http://127.0.0.1:5050/) by default.

You can edit the `docker-compose.yml` to change parameters of the deployment. You can also edit `/app/data/config.json` to change parameters of the server itself.

I also use an external bound volume for storing uploaded videos and output files. This can be modified for your own use, as this path might not be the same as mine.

## TODO

Add actual IP banning and rate limiting. Add animation export.

Build the contianer on github actions.

Move all config into env variables for docker, and get rid of config.json

```
docker build -t birdflight:latest .
```
