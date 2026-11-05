package featuretest;

import dev.reqcover.api.ForRequirement;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assumptions.assumeFalse;

abstract class AbstractLookupTest {
    @Test
    @ForRequirement(id = "#getBook/404")
    void inheritedUnknownBookIsNotFound() {
        assumeFalse(Boolean.getBoolean("ft.abortGetBook"), "aborted by ft.abortGetBook");
        assertTrue(new Library().getBook("9780134685991").isEmpty());
    }
}
