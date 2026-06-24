{
  pkgs ? import <nixpkgs> { },
}:

let
  python = pkgs.python3.override {
    self = python;
    packageOverrides = pyfinal: pyprev: {
      ipinfo = pyfinal.callPackage ./ipinfo.nix { };
    };
  };

  pythonWithOpencv = python.withPackages (ps: [
    (ps.opencv4.override {
      enableGtk3 = true;
    })
    ps.flask
    ps.waitress
    ps.ipinfo
  ]);
in
pkgs.mkShell {
  buildInputs = [
    pythonWithOpencv
    pkgs.pkg-config
    pkgs.stdenv.cc.cc.lib
    pkgs.py-spy
    pkgs.docker
    pkgs.docker-compose
    pkgs.ruff
  ];

  shellHook = ''
    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
    echo "Python with OpenCV ready (cv2 version: $(python -c 'import cv2; print(cv2.__version__)'))"
  '';
}
