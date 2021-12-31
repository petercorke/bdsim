
# Parameter types and defaults

The docstrings of bdsim blocks are parsed to determine the types and default values of all parameters.
This means that they need to conform to some simple guidelines.

`bdedit` parses the docstrings of all discovered blocks at startup time, and  will complain at runtime if it cannot parse a docstring.

Input values are checked when the `Update parameters` button is clicked, and type or value violations are notified by a popup.

## Default values


For assigning the default value for a parameter, expected format in param definition

```
:param myparam: ..., defaults to X
```

* Text up until `defaults to` is ignored, the rest is either a value that can be evaluated or a string
* If the value cannot be parsed it defaults to `None` 

### List

* If the value that follows `defaults to` is in the form of a list, there must be no spaces between values in the list, e.g. [0,0,0]

For example:

```
	frequency, defaults to 1
	the constant, defaults to None
	interpolation method, defaults to 'linear'
	denominator coefficients, defaults to [1,1]
	axis labels (xlabel, ylabel), defaults to ["X","Y"]
	Initial phase of signal in the range [0,1], defaults to 0
	duty cycle for square wave in range [0,1], defaults to 0.5
	extra keyword arguments passed to the function, defaults to {}
	pass in a reference to a dictionary instance, defaults to False
	extra positional arguments passed to the function, defaults to []
	signs associated with input ports, accepted characters: + or -, defaults to '++'
```

### One of a set

For parameters where input can be one of certain keywords, expected format in param definition:

```
:param myparam: ... one of: 'option1', 'option2' [default], 'option3'
```

* Text up until `one of:` is ignored
* After `one of:` every option is expected to be given as as string using **single quotes**
* Options are separated by commas
* The default value has `[default]` after the option string, but before the comma
* There should be no more text after last option
	
For example:

```
	type of waveform to generate, one of: 'sine', 'square' [default], 'triangle'
	frequency unit, one of: 'rad/s', 'Hz' [default]
```

### Range limit

For parameters where input must be within a range, expected format in param definition:

```
:param myparam: ... range [min, max]
```

* Text up to `range` is ignored
* The string after `range` bdedit is evaluated and the result is a list instance of length of 2 which is taken as the range, else an error message.
	
For example:

```
	duty cycle for square wave in range [0,1], defaults to 0.5
	Initial phase of signal in the range [0,1], defaults to 0
```
### Character subset

For parameters where input is a string that comprises a subset of characters:

```
:param myparam: 	... accepted characters: X or Y or Z
```

* Text up to `accepted characters:` is ignored
* Text after after `accepted characters:` is assumed to be a white-space separated list and the
 even elements are taken.  The odd elements are the keyword `or`.
* Values must be **not alphanumeric**, else ignored. 
* 	bdedit knows it has reached the end of the character options when there is no longer an `or` after a given value

	
For example:

```
	signs associated with input ports, accepted characters: + or -, defaults to '++'
	operations associated with input ports, accepted characters: * or /, defaults to '**'
```


## Parameter types

If for whatever reason a parameter type is not detected, bdedit will assign `str` as the default type. 


### Array like


If the keyword `array_like` is used in the type definition of a parameter.

#### No size restriction
```
:type myparam: ... or array_like, ...
:type myparam: ...	array_like ..., ...
:type myparam: ...	array_like, ...
```

* bdedit uses regex to search for `array_like[^(]` (not size restricted) 

For example:

```
	float or array_like, optional
	array_like, shape (N,) optional
	array_like, optional
	array_like
```

#### With size restriction

```
:type myparam: ...	or array_like(N), ...
:type myparam: ...	array_like(N) ..., ...
:type myparam: ...	array_like(N), ...
```

* bdedit uses regex to search for `array_like([0-9]+)` (size restricted)
* if a match, or multiple matches for `array_like` are found, each will be checked for size restrictions
		
???? 
* if size restrictions are found: 	parameter restricted to types: list or dict
* else if no size restrictions are found: parameter restricted to types: list, dict, int or float

For example:

```
	str or array_like(2) or array_like(4)
	str or array_like(2), optional
	str or array_like(2)
	array_like(2)
```	
	



### sequence or string

* If keyword `string` (instead of `str`) is found, the parameter will be granted types: 		list and str 
* If keyword `sequence`  found, the parameter will be granted types:		list

For example:

```
	callable or sequence of callables, optional
	sequence of strings
	bool or sequence
	sequence of time, value pairs
```

### Python native types

If any of the keywords `str`, `int`, `float`, `list`, `dict` are used are used in type definition of a parameter, bdedit will simply try to evaluate the given parameter value and test the resulting
type.

If keywords `callable`, `any` are used in type definition of a parameter, bdedit will consider the parameter of type `str`. 

The keyword `tuple` will be considered to be type `list` (JSON cannot distinguish `tuple` and `list`) 


