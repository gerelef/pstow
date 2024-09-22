#!/usr/bin/env -S python3.12 -S -OO
# From the documentation:
# >"If the readline module was loaded,
#  then input() will use it to provide elaborate line editing and history features."
import logging
import math
import os
import re
# noinspection PyUnresolvedReferences
import readline
import shlex
import shutil
import sys
from argparse import ArgumentParser
from copy import copy
from glob import iglob
from itertools import zip_longest
from pathlib import PosixPath
from typing import Iterable, final, Self, Optional, Callable, Iterator, TextIO

type StrPath = str | os.PathLike[str] | PosixPath


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(levelname)s: %(message)s"

    FORMATS = {
        logging.INFO: "%(message)s " + reset,  # use this for user-facing output
        logging.DEBUG: reset + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class PathError(RuntimeError):
    pass


# class & logger setup ripped straight out of here
# https://stackoverflow.com/a/56944256
class AbortError(RuntimeError):
    pass


class VPath(PosixPath):
    def vredirect(self, __old: StrPath, __new: StrPath) -> Self:
        """
        Virtual redirect; return a new VPath whose __old component is replaced by __new.
        """
        # this is dumb beyond belief, but here's what it does:
        #  since we need to create a target in a directory we own (and not our target's), we need to
        #  redirect it somehow; this will replace all instances of the target, with our absolute path
        #  and as a result, the resulting Tree will be ourselves (or some child)
        return VPath(str(self).replace(str(__old), str(__new), 1)).absolute()

    def vnext(self, other: Self) -> Self:
        """
        Get the next component in-line relative to another VPath. For example:
        self: /home/user/component
        other: /home/usr/component/something/else
        will return VPath("/home/usr/component/something")
        """
        if not isinstance(other, VPath):
            raise TypeError(f"No component can be traced between {self} for invalid type {type(other)}!")
        self_components = self.get_dir_parts(self)
        other_components = other.get_dir_parts(other)
        if self_components == other_components:
            return None

        previous_components: list[StrPath] = []
        for sc, oc in zip_longest(self_components, other_components):
            current_component = sc if sc else oc
            previous_components.append(current_component)
            if sc != oc:
                return VPath(*previous_components)
        return None

    @classmethod
    def get_dir_parts(cls, thing: Self | PosixPath | StrPath) -> tuple[str, ...]:
        """
        Return the true path towards a thing, removing filenames, and counting fs structure
        """
        if isinstance(thing, str):
            thing = VPath(thing)

        if thing.exists(follow_symlinks=False):
            return thing.absolute().parts if thing.is_dir() else thing.absolute().parts[:-1]
        return thing.absolute().parts


# AUTHOR'S NOTE:
# For future refence, a nice refactor would be to move the tree ops outside the class because it's bloated
#  but currently, I do not want to deal with multiple files for this particular project.
#  However, an ops @property would be the cool way to do it, with a TreeOperator(self) "bridge".
# Recursive-trim functions do not affect the filesystem, they just remove them from the tree.
@final
class Tree:
    REAL_USER_HOME = f"{str(VPath().home())}"

    def __init__(self, tld: VPath, profile: str = "default"):
        self.__tld: VPath = tld.absolute()
        self.profile: str = profile

        self.__tree: list[Self | VPath] = []
        self.__stowignore: Optional[Stowconfig] = None

    def __len__(self) -> int:
        """
        @return: The recursive length of structures, Trees and VPaths included.
        """
        length = len(self.tree)
        for branch in self.branches:
            length += len(branch)

        return length

    def __eq__(self, other: Self) -> bool:
        """
        Does not check for content and branch equality, just path equality.
        """
        # check that the type is tree, name is our name, and we have the same hash (in this order, short-circuit)
        return isinstance(other, Tree) and self.name == other.name and hash(self) == hash(other)

    def __ne__(self, other: Self) -> bool:
        """
        Inverse equality.
        """
        return not self == other

    def __contains__(self, other: Self | VPath) -> bool:
        """
        Non-recursive check if we contain an element.
        @param other: Element in question.
        @return: True if element is contained in this Tree, or deeper.
        """
        if other is None:
            return False
        self_parts = VPath.get_dir_parts(self.absolute())
        other_parts = VPath.get_dir_parts(other.absolute())

        # if the other parts are less than ours, meaning
        #  my/path/1
        #  my/path
        # it means that my/path is definitely not contained within our tree
        if len(other_parts) < len(self_parts):
            return False

        # zip_longest, not in reverse, since the other_parts might be in a subdirectory,
        #  we just want to check if the tld equivalent is us
        for spc, opc in zip(self_parts, other_parts):
            if spc != opc:
                return False

        return True

    def __repr__(self) -> str:
        return str(self.absolute())

    def __hash__(self) -> int:
        # combine the hashes of the path + a fixed offset, so thet trees are only
        #  compared against other trees regarding their uniqueness
        return hash(self.absolute()) + hash("TREE")

    def repr(self, indentation: int = 0) -> str:
        """
        @param indentation: indentation level.
        @return: Tree representation of the current tree.
        """

        def indent(indentation: int):
            tail_length = max((indentation - 1), 0)
            return f"{"─" * tail_length}{">" if tail_length else ""}"

        def shorten_name(p: Tree | VPath) -> str:
            ps = p.name if isinstance(p, VPath) else f"{p.name}/"
            # optionally, if the real user home exists in this path, substitute with ~
            if ps.startswith(Tree.REAL_USER_HOME):
                return ps.replace(Tree.REAL_USER_HOME, "~", 1)
            return ps

        out: list[str] = [f"\033[96m{indent(indentation)} \033[1m{shorten_name(self)}\033[0m"]
        for content in sorted(self.contents):
            out.append(f"\033[96m\033[93m{indent(indentation + 4)} \033[3m{shorten_name(content)}\033[0m")
        for branch in sorted(self.branches, key=lambda br: br.name):
            out.append(branch.repr(indentation=indentation + 4))
        return "\n\033[96m\033[0m".join(out)

    @property
    def stowignore(self):
        return self.__stowignore

    def absolute(self) -> VPath:
        """
        @return: Top-level directory, a VPath.
        """
        return self.__tld

    @property
    def name(self) -> str:
        return self.__tld.name

    @property
    def tree(self) -> list[Self | VPath]:
        return self.__tree

    @tree.setter
    def tree(self, element: Self | VPath):
        # subtree handling
        if isinstance(element, Iterable):
            self.__tree.extend(element)
            return

        self.__tree.append(element)

    @property
    def branches(self) -> Iterable[Self]:
        """
        Filter all the branches (subtrees) from the children, and return the iterator.
        """
        return list(filter(lambda el: isinstance(el, Tree), self.tree))

    @property
    def contents(self) -> Iterable[VPath]:
        """
        Filter all the contents (VPaths) from the children, and return the iterator.
        """
        return list(filter(lambda el: isinstance(el, VPath), self.tree))

    def traverse(self) -> Self:
        """
        Traverse the physical directory tree and populate self.
        """
        # the reason for this ugliness, is that os.walk is recursive by nature,
        #  and we do not want to recurse by os.walk, but rather by child.traverse() method
        try:
            _, directory_names, file_names = next(self.absolute().walk(follow_symlinks=False))
        except StopIteration:
            # stop iteration is called by os.walk when, on an edge case, pstow is called on ~
            return self

        for fn in file_names:
            pp = VPath(os.path.join(self.absolute(), fn))
            if fn == Stowconfig.STOWIGNORE_FN:
                self.__stowignore = Stowconfig(pp, self.profile)

            self.tree = pp

        for dn in directory_names:
            self.tree = Tree(self.absolute() / dn).traverse()

        return self

    def _vtrim_file(self, element: VPath, depth: int = math.inf) -> Self:
        """
        Internal usage only.
        Recursively trim the VPath element from the contents.
        Falls back to children if it doesn't exist.
        @param element: Element to be removed
        @param depth: Determines the maximum allowed depth to search.
        The default value is infinite.
        """
        if depth < 0:
            return self
        if element is None:
            raise RuntimeError(f"Expected VPath, got None?!")
        if not isinstance(element, VPath):
            raise RuntimeError(f"Expected VPath, got {type(element)}")

        removable_contents: Iterable[VPath] = list(filter(lambda pp: pp == element, self.contents))
        for rcont in removable_contents:
            # edge case for stowignore files:
            if rcont.name == Stowconfig.STOWIGNORE_FN:
                self.__stowignore = None

            self.tree.remove(rcont)

        # early exit
        if removable_contents:
            return self

        # if we didn't get any matches, the file wasn't ours to trim, check children
        for branch in self.branches:
            branch._vtrim_file(element, depth=depth - 1)

        return self

    def _vtrim_branch(self, removable_branch: Self, depth: int = math.inf) -> Self:
        """
        Internal usage only.
        Recursively trim the Tree branch, removing it from the branches.
        Falls back to children if it doesn't exist.
        @param removable_branch:
        @param depth: Determines the maximum allowed depth to search.
        The default value is infinite.
        """
        if depth < 0:
            return self
        # sanity checks
        if removable_branch is None:
            raise RuntimeError(f"Expected Tree, got None?!")
        if not isinstance(removable_branch, Tree):
            raise RuntimeError(f"Expected Tree, got {type(removable_branch)}")
        if removable_branch == self:
            raise RuntimeError(f"Expected other, got self?!")

        subtrees = list(filter(lambda el: el == removable_branch, self.branches))
        for subtree in subtrees:
            self.tree.remove(subtree)

        # early exit
        if subtrees:
            return self

        for branch in self.branches:
            branch._vtrim_branch(removable_branch, depth=depth - 1)

        return self

    def vtrim_content(self, thing: VPath | Self | StrPath, depth: int = math.inf) -> Self:
        """
        Driver/wrapper function to avoid duplication of .vtrim_file or .vtrim_branch
        """
        if isinstance(thing, str):
            thing = VPath(thing).absolute()
        # if thing is a directory, convert it to a Tree 
        if isinstance(thing, VPath) and thing.exists(follow_symlinks=False) and thing.is_dir():
            thing = Tree(thing)
        if isinstance(thing, Tree):
            self._vtrim_branch(thing, depth=depth)
            return self
        if isinstance(thing, VPath):
            self._vtrim_file(thing, depth=depth)
            return self

        raise TypeError(f"Cannot resolve trim_content for thing {str(thing)} type {type(thing)}!")

    def vtrim_file_rule(self, fn: Callable[[VPath, int], bool], depth: int = math.inf) -> Self:
        """
        Recursively apply business rule to all contents.
        @param fn: Business function that determines whether the element will be removed or not, with depth provided.
        Should return True for elements we want to remove, False for branches we do not.
        @param depth: Determines the maximum allowed depth to search.
        The default value is infinite.
        """
        if depth < 0:
            return self
        for branch in self.branches:
            branch.vtrim_file_rule(fn, depth=depth - 1)

        for pp in self.contents:
            if fn(pp, depth):
                # we do not want to descent to children branches while trimming, just this level
                self._vtrim_file(pp, depth=0)

        return self

    def vtrim_branch_rule(self, fn: Callable[[Self, int], bool], depth: int = math.inf) -> Self:
        """
        Apply business rule to branches.
        @param fn: Business function determines whether the element will be removed or not, with depth provided.
        Should return True for elements we want to remove, False for branches we do not.
        @param depth: Determines the maximum allowed depth to search.
        The default value is infinite.
        """
        if depth < 0:
            return self
        for branch in self.branches:
            branch.vtrim_branch_rule(fn, depth=depth - 1)

        for branch in self.branches:
            if fn(branch, depth):
                # we do not want to descent to children branches while trimming, just this level
                self._vtrim_branch(branch, depth=0)

        return self

    def vtrim_ignored(self, depth: int = math.inf) -> Self:
        """
        Recursively trim all the branches & elements,
        from the existing .stowignore files, in each tld (top-level directory).
        @param depth: Determines the maximum allowed depth to search.
        The default value is infinite.
        """
        if depth < 0:
            return self
        if self.stowignore:
            for ignorable in self.stowignore.ignorables:
                self.vtrim_content(ignorable, depth=depth)

        subtree: Tree
        for subtree in self.branches:
            subtree.vtrim_ignored(depth=depth - 1)

        return self

    def vmove_redirected(self, target: VPath, depth: int = math.inf) -> Self:
        """
        Move all redirectable virtual branches & elements, to their actual target.
        """
        if depth < 0:
            return self
        if self.stowignore:
            for redirectable in self.stowignore.redirectables:
                # trim the original vpath from the tree, since it won't be needed anymore in any tree
                #  this will affect files that are somehow redirected multiple times, and only the last one will be left
                self.vtrim_content(redirectable.src, depth=depth)

                for resolved_target in redirectable.resolve(target):
                    virtual_target = Tree(resolved_target.absolute().vredirect(target, self.absolute()))
                    self.vtouch(redirectable.src, virtual_target, depth=depth)

        subtree: Tree
        for subtree in self.branches:
            subtree.vmove_redirected(VPath(target / subtree.name), depth=depth - 1)

        return self

    def vtouch(self, src: VPath | Self, dst: Self, depth: int = math.inf) -> Self:
        """
        Create a new file or tree to a new destination.
        This changes the semantics of the virtual tree, and as such affects the ignore methods.
        """
        if depth < 0:
            return self
        if not src:
            raise RuntimeError(f"Cannot btouch non-existent {src} to dst {dst}!")
        if dst not in self:
            logger.warning(f"Skipping vtouch, we can't place dst {dst} in self {self} because it doesn't belong!")
            return self

        # if we're the eventual destination, place src in ourselves, and finish
        if dst == self:
            self.tree = src
            return self

        # if there's any existing Tree that is a component of our destination, delegate vtouch to that, and finish
        destination_components = list(filter(lambda st: dst in st, self.branches))
        for subtree in destination_components:
            subtree.vtouch(src, dst)
            return self

        # if we're part of the eventual destination, but we don't have any existing child
        # that can delegate the creation of this, we need to "do our part"
        # by creating our own partial Tree towards the eventual parent Tree
        #  and delegate vtouch to that
        if dst in self:
            self.tree = Tree(self.absolute().vnext(dst.absolute())).vtouch(src, dst)

        return self

    @classmethod
    def rsymlink(cls, tree: Self, target: VPath, fn: Callable[[VPath], bool], make_parents=True) -> None:
        """
        Recursively symlink a tree to destination.
        Inclusive, meaning the top-level directory name of Tree will be considered the same as destination,
        e.g., it will not make a new folder of the same name for the tld. However, it'll create a 1:1 copy
        for subtrees.
        If the directory doesn't exist, it'll be created.
        @param tree: Tree, whose contents we'll be moving.
        @param target: Top-level directory we'll be copying everything to.
        @param fn: Business rule the destination VPath will have to fulfill.
        Should return true for items we *want* to create.
        Sole argument is the destination (target) VPath.
        @param make_parents: equivalent --make-parents in mkdir -p
        """

        def prerequisites(dst: VPath) -> bool:
            """
            @return: True if OK to continue
            """
            if not fn(dst):
                logger.warning(f"Skipping {dst} due to policy...")
                return False

            if not target.exists(follow_symlinks=False):
                if not make_parents:
                    logger.error(f"Cannot softlink src {source} to dst {dst} without making parent dir {target}!")
                    return False
                dlink(tree, target)

            return True

        def dlink(srct: Tree, dst: VPath):
            # if this is not a virtual tree (aka, the srct actually exists)
            if srct.absolute().exists():
                logger.info(f"Creating destination which doesn't exist {dst}")
                mode = srct.absolute().stat(follow_symlinks=False).st_mode
                dst.mkdir(mode, parents=True, exist_ok=True)
                return
            logger.info(f"Creating virtual destination which doesn't exist {dst}")
            dst.mkdir(0o755, parents=True, exist_ok=True)

        def slink(src: VPath, dst: VPath):
            logger.info(f"Symlinking src {source} to {destination}")
            dst.unlink(missing_ok=True)
            dst.symlink_to(target=src.resolve(strict=True), target_is_directory=False)

        if not target.exists(follow_symlinks=False) and not make_parents:
            raise PathError(f"Expected valid target, but got {target}, which doesn't exist?!")
        if target.exists(follow_symlinks=False) and not target.is_dir():
            raise PathError(f"Expected valid target, but got {target}, which isn't a directory?!")

        source: VPath
        for source in tree.contents:
            destination = VPath(target / source.name)
            try:
                if not prerequisites(destination):
                    continue

                slink(source, destination)
            except Exception as e:
                logger.error(f"Got unexpected error {e} when softlinking {destination}?! Skipping...")
                continue

        branch: Tree
        for branch in tree.branches:
            destination_dir = VPath(target / branch.name)
            branch.rsymlink(tree=branch, target=destination_dir, fn=fn)


class RedirectEntry:
    def __init__(self, src: VPath | Tree, redirect: StrPath):
        self.__src = src
        self.__redirect = redirect

    def __str__(self) -> str:
        return f"RedirectEntry(src='{self.src}'), redirect={self.redirect}"

    @property
    def src(self) -> VPath | Tree:
        return self.__src

    @property
    def redirect(self) -> StrPath:
        return self.__redirect

    def resolve(self, target) -> Iterable[VPath]:
        """
        Resolve the redirectable for all valid Tree targets and return them.
        """
        # if the path doesn't exist, regardless if it's a globbable or not, return its parent
        if not list(Stowconfig.parse_glob_line(target, self.redirect)):
            yield VPath(os.path.join(target, self.redirect, self.src.name)).expanduser().parent.absolute()
            return

        for vp in Stowconfig.parse_glob_line(target, self.redirect):
            yield vp.absolute()
        return


class Stowconfig:
    STOWIGNORE_FN = ".stowconfig"
    IGNORE_SECTION_HEADER_TOK = "[ignore]"
    REDIRECT_SECTION_HEADER_TOK = "[redirect]"

    IF_PKG_BLOCK_REGEX = re.compile(r"\[(if-pkg:::)(.+)]")
    IF_NOT_PKG_BLOCK_REGEX = re.compile(r"\[(if-not-pkg:::)(.+)]")
    IF_PROFILE_BLOCK_REGEX = re.compile(r"\[(if-profile:::)(.+)]")
    IF_NOT_PROFILE_BLOCK_REGEX = re.compile(r"\[(if-not-profile:::)(.+)]")

    END_BLOCK_TOK = "[end]"
    COMMENT_PREFIX_TOK = "//"
    UNIGNORE_PREFIX_TOK = "!!"

    ERR_STRATEGY: Callable[[Exception], None] = lambda e: None

    def __init__(self, fstowignore: VPath, profile: str = "default"):
        """
        @param fstowignore: stowignore VPath
        """
        self.fstowignore = fstowignore
        self.parent = fstowignore.parent
        self.profile: str = profile

        self.__ignorables: list[VPath] = []
        self.__redirectables: list[RedirectEntry] = []
        self.__redirectables_sanitized = False

        self.__cached = False

    # noinspection PyMethodMayBeStatic
    def _skip_entries_until_block_end(self, sti: TextIO, supress=False):
        while (trimmed_line := next(sti).strip()) != Stowconfig.END_BLOCK_TOK:
            if not supress:
                logger.warning(f"Skipping block entry: {trimmed_line}")

    def _handle_if_block(self, strategy: Callable[[str], None], sti: TextIO,
                         header: str, prefix_to_strip: str, condition: Callable[[list[str]], bool]):
        contents: list[str] = shlex.split(
            header.removeprefix("[").removesuffix("]").removeprefix(prefix_to_strip).strip()
        )
        if not contents:
            logger.error(
                f"Skipping invalid {header} block due to unspecified contents after prefix."
            )
            self._skip_entries_until_block_end(sti)

        if not condition(contents):
            logger.warning(f"Couldn't fulfill condition for {header}. Skipping block contents...")
            self._skip_entries_until_block_end(sti, supress=True)
            return

        # if everything checks out, continue handling the if-pkg block w/ the current strategy
        while (trimmed_line := next(sti).strip()) != Stowconfig.END_BLOCK_TOK:
            # skip empty lines, and comments (which are line separated)
            if not trimmed_line or self._is_comment(trimmed_line):
                continue
            logger.info(f"Applying {header} entry: {trimmed_line}")
            strategy(trimmed_line)

    def _handle_if_pkg_block(self, strategy: Callable[[str], None], header: str, sti: TextIO) -> None:
        self._handle_if_block(
            strategy, sti, header, "if-pkg:::",
            lambda packages: all(map(shutil.which, packages))
        )

    def _handle_if_not_pkg_block(self, strategy: Callable[[str], None], header: str, sti: TextIO) -> None:
        self._handle_if_block(
            strategy, sti, header, "if-not-pkg:::",
            lambda packages: not all(map(shutil.which, packages))
        )

    def _handle_if_profile_block(self, strategy: Callable[[str], None], header: str, sti: TextIO) -> None:
        self._handle_if_block(
            strategy, sti, header, "if-profile:::",
            lambda profiles: self.profile in profiles
        )

    def _handle_if_not_profile_block(self, strategy: Callable[[str], None], header: str, sti: TextIO) -> None:
        self._handle_if_block(
            strategy, sti, header, "if-not-profile:::",
            lambda profiles: self.profile not in profiles
        )

    def _handle_ignore_lines(self, entry: str) -> None:
        def flatten_tree(iterable_tree: Tree | VPath) -> Iterable[VPath]:
            """
            Flatten any tree & return all its contents
            """
            if isinstance(iterable_tree, VPath) and not iterable_tree.is_dir():
                return [iterable_tree]
            contents = []
            for child in iterable_tree.absolute().iterdir():
                contents.extend(flatten_tree(child))
            return contents

        # if it's an inverted token, invert & bail!
        if entry.startswith(Stowconfig.UNIGNORE_PREFIX_TOK):
            for it in Stowconfig.parse_glob_line(self.parent, entry.removeprefix(Stowconfig.UNIGNORE_PREFIX_TOK)):
                [vp in self.__ignorables and self.__ignorables.remove(vp) for vp in flatten_tree(it)]
            return

        for it in Stowconfig.parse_glob_line(self.parent, entry):
            self.__ignorables.extend(flatten_tree(it))

    def _handle_redirect_lines(self, entry: str) -> None:
        entry_list = shlex.split(entry)
        # delimiter should be in the middle as :::
        if len(entry_list) != 3 or entry_list[1].strip() != ":::":
            logger.error(f"Skipping invalid redirect entry: {entry}")
            logger.error(f"NOT following the format \"my/path/file.txt\" ::: \"to/another/path/file.txt\" !")
            return None
        self.__redirectables_sanitized = False
        # both are globbable: a group of elements can be matched to a group of targets (N:M relationship)
        #  however, we can't evaluate destination globbables (if they even *are* globbables) right now, since we
        #  don't have the target, which is a requirement for matching this to paths
        s_src, s_dst = entry_list[0], entry_list[-1]  # first & last
        for redirected in Stowconfig.parse_glob_line(self.parent, s_src):
            self.__redirectables.append(RedirectEntry(redirected, s_dst))

    # noinspection PyMethodMayBeStatic
    def _is_comment(self, line: str) -> bool:
        return line.startswith(Stowconfig.COMMENT_PREFIX_TOK)

    def _parse(self) -> None:
        """
        Resolve the structure of a STOWIGNORE_FN & cache results.
        """
        self.__cached = True
        self.__redirectables_sanitized = False
        strategy: Callable[[str], None] = self._handle_ignore_lines
        with open(self.fstowignore, "r", encoding="UTF-8") as sti:
            for line in sti:
                trimmed_line = line.strip()
                # skip empty lines, and comments (which are line separated)
                if not trimmed_line or self._is_comment(trimmed_line):
                    continue
                match trimmed_line:
                    case Stowconfig.IGNORE_SECTION_HEADER_TOK:
                        strategy = self._handle_ignore_lines
                        continue  # eat line because it's a header
                    case Stowconfig.REDIRECT_SECTION_HEADER_TOK:
                        strategy = self._handle_redirect_lines
                        continue  # eat line because it's a header
                    case _:
                        # handle cases that are not computable @ 'compile' time
                        if Stowconfig.IF_PKG_BLOCK_REGEX.fullmatch(trimmed_line):
                            self._handle_if_pkg_block(strategy, trimmed_line, sti)
                            continue  # eat line because it's an [end] tok
                        if Stowconfig.IF_NOT_PKG_BLOCK_REGEX.fullmatch(trimmed_line):
                            self._handle_if_not_pkg_block(strategy, trimmed_line, sti)
                            continue  # eat line because it's an [end] tok
                        if Stowconfig.IF_PROFILE_BLOCK_REGEX.fullmatch(trimmed_line):
                            self._handle_if_profile_block(strategy, trimmed_line, sti)
                            continue  # eat line because it's an [end] tok
                        if Stowconfig.IF_NOT_PROFILE_BLOCK_REGEX.fullmatch(trimmed_line):
                            self._handle_if_not_profile_block(strategy, trimmed_line, sti)
                            continue  # eat line because it's an [end] tok

                strategy(trimmed_line)

    @property
    def ignorables(self) -> Iterable[VPath]:
        try:
            if not self.__cached:
                self._parse()
        except Exception as e:
            logger.error(f"Got {e} while parsing stowconfig.")
            Stowconfig.ERR_STRATEGY(e)

        # don't leak reference
        return copy(self.__ignorables)

    @property
    def redirectables(self) -> Iterable[RedirectEntry]:
        """
        Returns an Iterator of VPath (src) to set of targets (Tree) (1:N)
        """
        try:
            if not self.__cached:
                self._parse()
        except Exception as e:
            logger.error(f"Got {e} while parsing stowconfig.")
            Stowconfig.ERR_STRATEGY(e)
        if not self.__redirectables_sanitized:
            self.__redirectables_sanitized = True
            self.__redirectables = list(filter(lambda t: t.src not in self.ignorables, self.__redirectables))
        return copy(self.__redirectables)

    @staticmethod
    def parse_glob_line(parent: VPath, tail: StrPath) -> Iterator[VPath | Tree]:
        def parse_entry(entry: str) -> VPath | Tree:
            pp = VPath(entry).expanduser().absolute()
            # return tree if it's a dir
            if pp.is_dir():
                return Tree(pp)
            # return a VPath for regular files
            return pp

        # the fact that we're forced to use os.path.join, and not VPath(tld / p)
        #  is evil, and speaks to the fact that the development of these two modules (iglob & Path)
        #  was completely disjointed
        for p in iglob(os.path.join(parent / tail), recursive=True):
            yield parse_entry(p)
        return


@final
class Stower:
    def __init__(self,
                 source: VPath,
                 destination: VPath,
                 skippables: list[VPath] = None,
                 force=False,
                 make_parents=False,
                 no_redirects=False,
                 profile="default"):
        self.src = source
        self.dest = destination
        self.skippables = skippables

        # empty flags
        self.force = force
        self.make_parents = make_parents
        self.no_redirects = no_redirects

        # aka working tree directory, reflects the current filesystem structure
        self.src_tree: Tree = Tree(self.src, profile=profile)

    def _prompt(self) -> bool:
        """
        Prompt the user for an input, [Y/n].
        @return: True if user selects yes, False for any other case.
        """
        logger.info("The following action is not reversible.")
        while True:
            try:
                reply = input(
                    f"Do you want to link the tree to destination \x1b[31;1m{self.dest}/...\x1b[0m [Y/n]? "
                ).lower()
            except KeyboardInterrupt:
                return False
            except EOFError:
                # this catch doesn't work through the IDE, but in regular runs it works
                #  leave it as-is
                return False

            yes = reply == "y" or reply == "yes"
            no = reply == "n" or reply == "no"
            if not yes and not no:
                logger.info(f"Invalid reply {reply}, please answer with y/yes for Yes, or n/no for no.")
                continue
            return yes

    def stow(self, interactive: bool = True, dry_run: bool = False):
        """
        @param interactive: if True stow will not ask permission for things that affect the filesystem.
        @param dry_run: if True stow will actually affect the destination filesystem.
        @raise PathError: if src and dest are the same.
        @raise AbortError: if the aborts recursive symlink operation is aborted.
        """
        if self.src == self.dest:
            raise PathError("Source cannot be the same as destination!")

        # first step: create the tree of the entire src folder
        self.src_tree.traverse()
        # early exit for empty trees
        if not len(self.src_tree):
            logger.info(f"{self.src_tree.repr()}")
            logger.warning(f"Source tree is empty? Exiting...")
            sys.exit(1)

        # (optional) second step: virtual move all redirectables first
        #  this step is done here, so we don't get any invalid entries when ignoring things that
        #  were previously considered redirectables
        #  the fact of the matter is, we'd have to remove ignored files *again* if this were to happen as a seconds step
        #  this is a concern regarding the internals, and is obviously not the best, however, even if the capability
        #  is eventually added, it's still sane to do this first
        if not self.no_redirects:
            self.src_tree.vmove_redirected(self.dest)

        # third step: apply preliminary business rule to the tree:
        #  trim explicitly excluded items
        # the reason we're doing the explicitly excluded items first, is simple
        #  the fact is that explicitly --exclude item(s) will most likely be less than the ones in .stowignore
        #  so, we're probably saving time since we don't have to trim .stowignored files that do not apply
        for thing in filter(lambda sk: sk in self.src_tree, self.skippables):
            self.src_tree.vtrim_content(thing)

        # fourth step: trim the tree from top to bottom, for every .stowignore we find, we will apply
        #  the .stowignore rules only to the same-level trees and/or files, hence, provably and efficiently
        #  trimming all useless paths
        self.src_tree.vtrim_ignored()

        # sixth step: apply preliminary business rule to the tree:
        #  trim empty branches to avoid creation of directories whose contents are ignored entirely
        self.src_tree.vtrim_branch_rule(lambda br, __: len(br) == 0)

        logger.info(f"{self.src_tree.repr()}")
        # optional seventh step: ask for user permission if interactive
        # - if the current run is interactive, must be false
        # - if the current run is interactive, and is a dry run, must be false
        # - if the current run isn't interactive, and is a dry run, must be false
        # - if the current run isn't interactive, and isn't a dry run, must be true
        approved = not interactive and not dry_run
        if not dry_run and interactive:
            approved = self._prompt()
        if not approved:
            raise AbortError("Aborted the rsymlink due to policy.")

        # eighth step: symlink the populated tree
        # since all of these rules are explicit business rules, and could be substituted for whatever in the future
        #  this is a pretty elegant solution. I've already refactored (one) case, and it's proved its value
        logger.info("Linking...")
        # overwrite just symlinks that already exist rule
        exists_rule = lambda dpp: dpp.is_symlink() if dpp.exists(follow_symlinks=True) else True
        if self.force:
            # overwrite everything rule
            exists_rule = lambda dpp: True
        # overwrite if not in the original tree rule
        #  here, we're comparing the absolute VPath of the original tree,
        #  with the target (destination) VPath
        #  if they're the same, we do NOT want to overwrite the tree
        keep_original_rule = lambda dpp: dpp not in self.src_tree
        # If we'd overwrite the src tree by copying a specific link to dest, abort due to fatal conflict.
        #  For example, consider the following src structure:
        #  dotfiles
        #    > dotfiles
        #  gets stowed to destination /.../dotfiles/.
        #  the inner dotfiles/dotfiles symlink to dotfiles/.
        #  would overwrite the original tree, resulting in a catastrophic failure where everything is borked.
        Tree.rsymlink(
            self.src_tree,
            self.dest,
            make_parents=self.make_parents,
            fn=lambda dpp: exists_rule(dpp) and
                           keep_original_rule(dpp),
        )


def get_arparser() -> ArgumentParser:
    ap = ArgumentParser(
        "A spiritual reimplementation of GNU Stow, but simpler, for tinkerers."
    )
    ap.add_argument(
        "--source", "-s",
        type=str,
        required=False,
        default=os.getcwd(),
        help="Source directory links will be linked from."
    )
    ap.add_argument(
        "--target", "-t",
        type=str,
        required=False,
        default=None,
        help="Target (destination) directory links will be linked to."
    )
    ap.add_argument(
        "--enforce-integrity", "-i",
        required=False,
        action="store_true",
        default=False,
        help="Enforce integrity of any .stowconfig encountered; a.k.a. stop at any error."
    )
    ap.add_argument(
        "--force", "-f",
        required=False,
        action="store_true",
        default=False,
        help="Force overwrite of any conflicting file. This WILL overwrite regular files!"
    )
    ap.add_argument(
        "--yes", "-y",
        required=False,
        action="store_true",
        default=False,
        help="Automatically assume 'yes' for any user prompt. Dangerous flag, possibly destructive!"
    )
    ap.add_argument(
        "--exclude", "-e",
        required=False,
        nargs="+",
        default=[],
        help="Exclude (ignore) a specific directory when copying the tree. Multiple values can be given. "
             "Symlinks are not supported as exclusion criteria."
    )
    ap.add_argument(
        "--profile", "-p",
        required=False,
        type=str,
        default="default",
        help="Profile to use when loading .stowconfigs."
             "This will affect all if-profile and if-not-profile blocks accordingly. "
    )
    ap.add_argument(
        "--no-parents", "-n",
        required=False,
        action="store_true",
        default=False,
        help="Don't make parent directories as we traverse the tree in destination, even if they do not exist."
    )
    ap.add_argument(
        "--no-redirects", "-r",
        required=False,
        action="store_true",
        default=False,
        help="Don't respect redirects in any encountered stowconfig."
    )
    ap.add_subparsers(dest="command", required=False).add_parser(
        "status",
        help="Echo the current status of the stow source."
    )

    return ap


def get_logger() -> logging.Logger:
    # create logger
    # noinspection PyShadowingNames
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(CustomFormatter())

    logger.addHandler(ch)
    return logger


def main():
    args = get_arparser().parse_args()
    try:
        is_dry = args.command == "status"
        if not is_dry and not args.target:
            logger.error("Target must be set for non-dry runs.")
            sys.exit(2)

        Stowconfig.ERR_STRATEGY = sys.exit if args.enforce_integrity else None

        # source & destination MUST exist & be valid!
        source = VPath(args.source).resolve(strict=True)
        destination = VPath(args.target if not is_dry else Tree.REAL_USER_HOME).resolve(strict=True)
        excluded = [VPath(str_path).absolute() for str_path in args.exclude]

        Stower(
            source, destination,
            skippables=excluded,
            force=args.force,
            make_parents=not args.no_parents,
            no_redirects=args.no_redirects,
            profile=args.profile
        ).stow(
            interactive=not args.yes,
            dry_run=args.command == "status"
        )
    except AbortError:
        logger.warning("Aborting.")
    except FileNotFoundError as e:
        logger.error(f"Couldn't find file!\n{e}")
    except PathError as e:
        logger.error(f"Invalid operation PathError!\n{e}")


if __name__ == "__main__":
    # set for really deep trees
    sys.setrecursionlimit(10_000_000)
    logger = get_logger()

    main()
