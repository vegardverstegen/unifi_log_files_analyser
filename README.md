# UniFi Log File Analyser
Tools developed to extract evidence from log files created by the Ubiquiti Unifi System

The tools are designed to work together.

## Processing
processing.py takes two arguments. The first being the type of device the files are from. This can either be "usw" for Unifi Switch, or "usg" for Unifi Security Gateway. The second argument is the path to the folder containing the files. The program will analyse "messages" from both devices and "vpn" from the security gateway. Other files will be ignored.

## Analyzing
analysis.py takes one argument, the location of the output folder of the previous program. It then outputs a folder containing any visuals created, a pdf report and a file with hashes. To search for the location of the ip addresses from the "vpn" file an API is used. The API accepts a limit amount of requests each day. A free API key can be created at https://app.ipgeolocation.io/ and replaced with the apiKey in the main function. 