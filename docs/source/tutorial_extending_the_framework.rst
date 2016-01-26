Extending the Framework
=======================

Kitty comes with implementation for several targets and controllers,
ready to be used. This page will explain how to create new classes to
meet your needs.

The API of all classes is mainly state-oriented. This means that the
functions are called upon state, and does not specify an action by their
names. For example, the ``BaseController`` methods are ``setup``,
``teardown``, ``pre_test`` and ``post_test``, not ``prepare_victim``,
``stop_victim``, ``restart_victim`` etc.

Controllers
-----------

All controllers inherit from ``BaseController`` (
kitty/controllers/base.py ), client controllers need to support
triggering, so they have an extended API.

Server Controller
~~~~~~~~~~~~~~~~~

Base Class: ``kitty.controllers.base.BaseController``

Methods
```````
``setup(self)``: Called at the beginning of the fuzzing session, this
is the time for initial settings.

``teardown(self)``: Called at the end of the fuzzing session, this is
the time for cleanup and shutdown of the victim.

``pre_test(self, test_number)``: Called before each test. should call
super if overriden.

``post_test(self)``: Called after each test. should call super if
overriden.

Members
```````

``report``: A ``Report`` object, add elements for it as needed

Client Controller
~~~~~~~~~~~~~~~~~

Base Class: **kitty.controllers.base.ClientController**

Methods
```````

``trigger(self)``: client transaction triggering

Monitor
-------

Base Class: ``kitty.monitros.base.BaseMonitor``

A monitor is running on a separate thread. A generic thread function
with a loop is running by default, and calls ``_monitor_func``, which
should be overriden by any monitor implementation. Not that this
function is called in a loop, so there is no need to perform a loop
inside it.

Methods
~~~~~~~

``setup(self)``: >Called at the beginning of the fuzzing session, this
is the time for initial settings. should call super if overriden.

``teardown(self)``: >Called at the end of the fuzzing session, this is
the time for cleanup and shutdown of the monitor. should call super if
overriden.

``pre_test(self, test_number)``: >Called before each test. should call
super if overriden.

``post_test(self)``: >Called after each test. should call super if
overriden.

``_monitor_func(self)``: >Called in a loop once the monitor is setup.
Unless there are specific needs, there is no need to implement stop
mechanism or endless loop inside this function, as they are implemented
by its wrapper. See the implementation of SerialMonitor
(kitty/monitors/serial.py) for example.

Members
~~~~~~~

``report``: >A ``Report`` object, add elements for it as needed

Target
------

Each target should inherit from ``ServerTarget`` or ``ClientTarget``,
both inherit from ``BaseTarget``. All methods in ``BaseTarget`` are
relevant to ``ServerTarget`` and ``ClientTarget`` as well.

Base Target
~~~~~~~~~~~

Base Class: **kitty.targets.base.BaseTarget**
