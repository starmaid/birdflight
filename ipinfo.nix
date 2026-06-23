# toolz.nix
{
  lib,
  buildPythonPackage,
  fetchPypi,
  setuptools,
  requests,
  cachetools,
  aiohttp,
}:

buildPythonPackage rec {
  pname = "ipinfo";
  version = "5.3.0";
  src = fetchPypi {
    inherit pname version;
    hash = "sha256-eVP2ak/Sio8oCLNTQC5ZXYMQpFUAj5VOGoeMzntOcTM=";
  };

  # do not run tests
  doCheck = false;

  # specific to buildPythonPackage, see its reference
  pyproject = true;

  build-system = [ setuptools ];

  dependencies = [ 
    requests
    cachetools
    aiohttp
  ];
}
