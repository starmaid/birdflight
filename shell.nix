{ pkgs ? import <nixpkgs> {} }:

let
  pythonWithOpencv = pkgs.python3.withPackages (ps: [
    (ps.opencv4.override {
        enableGtk3 = true;
      })
  ]);
in
pkgs.mkShell {
  buildInputs = [
    pythonWithOpencv
    pkgs.pkg-config
    pkgs.stdenv.cc.cc.lib
  ];

  shellHook = ''
    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
    echo "Python with OpenCV ready (cv2 version: $(python -c 'import cv2; print(cv2.__version__)'))"
  '';
}