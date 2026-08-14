# Security

Please do not open public issues for vulnerabilities that could expose users or hosted deployments. Contact the maintainer privately through the repository owner's GitHub profile.

Sheet2MIDI executes locally installed OMR binaries. Treat custom backend executables and untrusted container images as code execution. The built-in adapters never use shell interpolation; commands are passed as argument arrays.
