class Serializable:
    """
    The ``Serializable`` class provides three essential methods for: ensuring uniqueness
    amongst necessary data (1), saving (2) and loading (3) of this data that is needed
    for the reconstruction of a Block Diagram.
    """

    def __init__(self):
        """
        This method extracts the unique identification number of the class instance
        that calls this method, and stores it as a variable within that class instance.
        """
        self.id = id(self)

    def serialize(self):
        """
        This method is inherited and overwritten by all classes that have graphical
        components related to them (``Scene``, ``Block``, ``Socket`` and ``Wire``).
        This allows those classes to package (save) essential variables necessary
        for the later reconstruction of those class instances, into a JSON file.
        """
        raise NotImplemented()

    def deserialize(self, data, hashmap={}):
        """
        This method is inherited and overwritten by all classes that have graphical
        components related to them (``Scene``, ``Block``, ``Socket`` and ``Wire``).
        This allows those classes to un-package (load) the data stored within the
        saved JSON file in order to reconstruct the respective class instance.

        :param data: a Dictionary of essential data for reconstructing a Block Diagram
        :type data: OrderedDict, required
        :param hashmap: a Dictionary for of the same data, but used for simpler mapping
        of variables to class instances
        :type hashmap: Dict, required
        """
        raise NotImplemented()
