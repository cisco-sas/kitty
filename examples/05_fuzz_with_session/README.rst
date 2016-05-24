Server Fuzzer - Fuzz With Session
=================================


This fuzzer performs server fuzzing with session enabled.


Note
----

*session_server.py* is our demo target, it's a TCP server and listen on port 9999.
To communicate with *session_server* you need request a specific session for each connection.
You must use correct session with op_code(2) to send data to *session_server*, otherwise server will not response your request.

For more details, please check the docs in *session_server.py*

Usage
-----

1. In terminal A: ``python session_server.py``
2. In terminal B: ``python runner.py``
