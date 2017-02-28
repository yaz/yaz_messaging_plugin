import difflib
import io
import yaz
import yaml
import copy
import collections
import itertools
import re
import glob
import os
import os.path

from .log import logger
from .loader import OrderedDictLoader


class Messaging(yaz.BasePlugin):
    dirs = ["src/*/Bundle/*/Resources/translations/"]

    def __init__(self):
        logger.debug("translation directories: %s", self.dirs)

    @yaz.task
    def check(self, depth: int = 666, indent: int = 4):
        return self.cleanup(syntax_changes_strategy="fail", duplicate_key_strategy="fail", sync_strategy="fail", depth_strategy="fail", depth=depth, indent=indent)

    @yaz.task(changes_strategy__choices=["overwrite", "ask", "fail"],
              duplicate_key_strategy__choices=["first", "last", "ask", "fail"],
              sync_strategy__choices=["use-key", "ask", "ignore", "fail"],
              depth_strategy__choices=["join", "ask", "fail"])
    def cleanup(self, changes_strategy="ask", duplicate_key_strategy="ask", sync_strategy="ask", depth_strategy="ask", depth=666, indent=4):
        for domain, files in self.get_message_files():
            domains = {}
            for file in files:
                logger.debug("%s %s", domain, files)
                messages = self.get_messages_from_file(file)
                print(messages)
                domains[file] = self.resolve_duplicate_keys(duplicate_key_strategy, messages)

            print(domains)
            domains = self.resolve_message_sync(sync_strategy, domains)

            for file, messages in domains.items():
                try:
                    messages = self.resolve_message_depth(depth_strategy, depth, messages)
                except Exception as error:
                    raise RuntimeError("{} in file {}".format(error, file))
                self.resolve_changes(changes_strategy, file, messages, indent)

        return None

    def resolve_duplicate_keys(self, strategy, messages):
        """Given a STRATEGY and a dict with possibly duplicate messages, return a non-duplicate dict

        When there are more than one possible messages,
        the STRATEGY will decide how the duplication is resolved.
        The following STRATEGY options are available:
        - fail: raises a RuntimeError
        - first: chooses the first defined message and ignores any others
        - last: chooses the last defined message and ignores any others
        - ask: lets the user choose the message

        MESSAGES is a dict in the form:
        { translation_key: [first_translation_value, second_translation_value, ...] }

        RETURNS a dict in the form:
        { translation_key: translation_value }
        """
        assert isinstance(strategy, str), type(strategy)
        assert isinstance(messages, dict), type(dict)
        assert all(isinstance(key, str) for key in messages.keys())
        assert all(isinstance(value, list) for value in messages.values())
        assert all(all(isinstance(message, str) for message in value) for value in messages.values())
        if strategy == "fail":
            for key, value in messages.items():
                if len(value) > 1:
                    raise RuntimeError("translatable \"{}\" has multiple possible values: \"{}\"".format(key, value))
            return dict((key, value[0]) for key, value in messages.items())
        if strategy == "first":
            return dict((key, value[0]) for key, value in messages.items())
        if strategy == "last":
            return dict((key, value[-1]) for key, value in messages.items())
        if strategy == "ask":
            raise NotImplementedError("todo: implement duplicate_strategy=\"ask\" strategy")

    def resolve_changes(self, strategy, file, messages, indent):
        print(messages)
        buffer = io.StringIO()
        yaml.dump(messages, buffer, default_flow_style=False, width=1024 * 5, indent=indent)
        requires_changes = buffer.read() != open(file, "r").read()

        if requires_changes:
            buffer.seek(0)
            logger.debug("changes detected in file \"%s\"", file)

            if strategy == "fail":
                raise RuntimeError("changes detected in file \"{}\"".format(file))
            if strategy == "overwrite":
                with open(file, "w") as output:
                    for line in buffer.readlines():
                        print("###", line)
                        output.write(line)
            if strategy == "ask":
                diff = difflib.context_diff(
                    open(file, "r").readlines(),
                    buffer.readlines(),
                    "original {}".format(file),
                    "proposed {}".format(file)
                )
                for line in diff:
                    print(line.rstrip())
                raise NotImplementedError("todo: implement syntax_changes_strategy=\"ask\" strategy")

    def resolve_message_depth(self, strategy, depth, messages):
        assert isinstance(depth, int), type(depth)
        assert isinstance(messages, dict), type(dict)
        assert all(isinstance(key, str) for key in messages.keys())
        assert all(isinstance(value, str) for value in messages.values())
        root = dict()
        for keys, value in sorted(messages.items()):
            keys = keys.split(".", depth)
            layer = root
            prefix = ""
            for key in keys[:-1]:
                if prefix:
                    key = ".".join([prefix, key])
                    prefix = ""

                parent_layer = layer
                try:
                    layer = layer[key]
                except KeyError:
                    layer[key] = layer = dict()

                if isinstance(layer, str):
                    if strategy == "ask":
                        raise NotImplementedError("todo: implement depth_strategy=\"ask\" strategy")

                    if strategy == "join":
                        prefix = key
                        layer = parent_layer
                        continue

                    if strategy == "fail":
                        raise RuntimeError("conflicting keys when expanding path \"{}\"".format(".".join(keys)))

            key = keys[-1]
            if prefix:
                key = ".".join([prefix, key])
            layer[key] = value

        return root

    def resolve_message_sync(self, strategy, domains):
        assert isinstance(strategy, str), type(strategy)
        assert isinstance(domains, dict), type(domains)
        assert all(isinstance(key, str) for key in domains.keys())
        assert all(isinstance(value, dict) for value in domains.values())
        assert all(all(isinstance(key, str) for key in value.keys()) for value in domains.values())
        assert all(all(isinstance(message, str) for message in value.values()) for value in domains.values())
        all_keys = set()
        all_keys.update(*domains.values())

        if all(len(all_keys) == len(messages) for messages in domains.values()):
            # all domains have all the messages, no need to do anything
            return domains

        if strategy == "ignore":
            return domains

        if strategy == "fail":
            for file, messages in domains.items():
                for key in all_keys.difference(messages.keys()):
                    raise RuntimeError("translatable \"{}\" is not set in \"{}\"".format(key, file))

        domains = copy.deepcopy(domains)
        if strategy == "use-key":
            for messages in domains.values():
                for key in all_keys.difference(messages.keys()):
                    messages[key] = key

        if strategy == "ask":
            raise NotImplementedError("todo: implement duplicate_strategy=\"ask\" strategy")

        return domains

    def get_messages_from_file(self, file):
        """Read messages from a yml file and return a dict

        The returned dictionary contains a single key for every translatable string,
        however, as it is possible to have valid yml with duplicate keys, every key
        points to a list containing one or more translations.

        For example, the the yml file:
            foo.bar: A
            foo:
               bar: B

        Will return:
            {"foo.bar": ["A", "B"]}
        """
        assert isinstance(file, str), type(file)

        def recursion(messages, key, value):
            assert isinstance(messages, dict), type(messages)
            assert isinstance(key, str), type(key)

            if isinstance(value, dict):
                for postfix, value in value.items():
                    assert isinstance(postfix, str), [file, key, postfix, value]
                    recursion(messages, ".".join([key, postfix]), value)
            elif isinstance(value, str):
                messages[key[1:]].append(value)

            return messages

        return recursion(collections.defaultdict(list), "", yaml.load(open(file, "r"), OrderedDictLoader))

    def get_message_files(self):
        """Iterate over available message files grouped by directory and domain"""
        for dir_pattern in self.dirs:
            for dir in glob.glob(dir_pattern):
                files = [re.match(r"^(?P<filename>(?P<domain>\w+)[.](?P<language>\w{2})[.]yml)$", file) for file in sorted(os.listdir(dir))]
                files = [file.groupdict() for file in files if file]
                for domain, files in itertools.groupby(files, lambda file: file["domain"]):
                    yield domain, [os.path.join(dir, file["filename"]) for file in files]