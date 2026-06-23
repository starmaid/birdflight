{
  lib,
  buildPythonPackage,
  fetchPypi,
  setuptools,
  aiohttp,
  cachetools,
  requests,
}:

buildPythonPackage rec {
  pname = "ipinfo";
  version = "5.3.0";
  pyproject = true;

  src = fetchPypi {
    inherit pname version;
    hash = "sha256-eVP2ak/Sio8oCLNTQC5ZXYMQpFUAj5VOGoeMzntOcTM=";
  };

  build-system = [ setuptools ];

  dependencies = [ 
    requests
    cachetools
    aiohttp
  ];

  meta = {
    homepage = "https://github.com/ipinfo/python";
    description = "Official Python Library for IPinfo API";
    license = lib.licenses.apsl20;
    platforms = lib.platforms.all;
    maintainers = [ ];
  };
}
