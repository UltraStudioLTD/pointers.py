import ctypes
import sys
from .pointer import Pointer
from ._cstd import c_malloc, c_free, c_realloc
from typing import TypeVar, Generic, NoReturn

__all__ = (
    "IsMallocPointerError",
    "MallocPointer",
    "malloc",
    "free",
    "realloc"
)


T = TypeVar("T")


class IsMallocPointerError(Exception):
    """Raised when trying perform an operation on a malloc pointer that isn't supported."""  # noqa

    pass


class MallocPointer(Pointer, Generic[T]):
    """Class representing a pointer created by malloc."""

    def __init__(
        self,
        address: int,
        size: int,
        assigned: bool = False
    ) -> None:
        self._address = address
        self._size = size
        self._freed = False
        self._assigned = assigned

    @property
    def freed(self) -> bool:
        """Whether the allocated memory has been freed."""
        return self._freed

    @freed.setter
    def freed(self, value: bool) -> None:
        self._freed = value

    @property
    def assigned(self) -> bool:
        """Whether the allocated memory has been assigned a value."""
        return self._assigned

    @assigned.setter
    def assigned(self, value: bool) -> None:
        self._assigned = value

    @property
    def type(self) -> NoReturn:
        """Type of the pointer."""
        raise IsMallocPointerError("malloc pointers do not have types")

    @property
    def size(self) -> int:
        """Size of the memory."""
        return self._size

    @size.setter
    def size(self, value: int) -> None:
        self._size = value

    def assign(self, _) -> NoReturn:
        """Point to a different address."""
        raise IsMallocPointerError("cannot assign to malloc pointer")

    def __repr__(self) -> str:
        return f"<pointer to allocated memory at {hex(self.address)}>"

    def move(self, data: Pointer[T]) -> None:
        """Move data to the allocated memory."""
        if self.freed:
            raise MemoryError("memory has been freed")

        bytes_a = (ctypes.c_ubyte * sys.getsizeof(~data)) \
            .from_address(data.address)

        ptr = self.make_ct_pointer()
        byte_stream = bytes(bytes_a)

        try:
            ptr.contents[:] = byte_stream
        except ValueError as e:
            raise MemoryError(
                f"object is of size {len(byte_stream)}, while memory allocation is {len(ptr.contents)}"  # noqa
            ) from e

        self.assigned = True

    def make_ct_pointer(self):
        return ctypes.cast(
            self.address,
            ctypes.POINTER(ctypes.c_char * self.size)
        )

    def dereference(self):
        """Dereference the pointer."""
        if self.freed:
            raise MemoryError("memory has been freed")

        if not self.assigned:
            raise MemoryError("pointer has no value")

        return super().dereference()


def malloc(size: int) -> MallocPointer:
    """Allocate memory for a given size."""
    address = c_malloc(size)
    return MallocPointer(address, size)


def free(target: MallocPointer):
    """Free allocated memory."""
    ct_ptr = target.make_ct_pointer()
    c_free(ct_ptr)
    target.freed = True


def realloc(target: MallocPointer, size: int) -> None:
    """Resize a memory block created by malloc."""
    ct_ptr = target.make_ct_pointer()
    c_realloc(ct_ptr, size)
    target.size = size