package featuretest;

import dev.reqcover.api.ForRequirement;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestFactory;
import org.junit.jupiter.api.condition.DisabledIfSystemProperty;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.DynamicTest.dynamicTest;

class LibraryTest extends AbstractLookupTest {
    private static final String ISBN = "9780134685991";

    private static Library libraryWithOneBook() {
        Library library = new Library();
        library.addBook(ISBN, "Effective Java");
        return library;
    }

    private static boolean broken(String name) {
        return Boolean.getBoolean("ft." + name);
    }

    @Test
    @ForRequirement(id = "#listBooks/200")
    void plainTestListsBooksSortedByTitle() {
        Library library = new Library();
        library.addBook("9780000000002", "Refactoring");
        library.addBook("9780000000001", "Clean Code");
        List<String> titles = library.listBooks().stream().map(Book::title).toList();
        List<String> expected = broken("breakListBooks")
            ? List.of("Refactoring", "Clean Code")
            : List.of("Clean Code", "Refactoring");
        assertEquals(expected, titles);
    }

    @Test
    @ForRequirement(id = "#addBook/201/trimsTitle")
    @ForRequirement(id = "#getBook/200")
    void repeatedAnnotationTrimsTitleAndFindsBook() {
        Library library = new Library();
        library.addBook(ISBN, "  Effective Java  ");
        assertEquals("Effective Java", library.getBook(ISBN).orElseThrow().title());
    }

    @Test
    @ForRequirement(id = "#ping")
    void operationWithoutResponsesIsARequirement() {
        assertEquals("pong", new Library().ping());
    }

    @Test
    @DisabledIfSystemProperty(named = "ft.disableBlankTitle", matches = "true")
    @ForRequirement(id = "#addBook/400/blankTitle")
    void disableableRejectsBlankTitle() {
        assertEquals(Status.BAD_REQUEST, new Library().addBook(ISBN, "   "));
    }

    @ParameterizedTest
    @ValueSource(strings = {"123", "97801346859911", "978013468599X"})
    @ForRequirement(id = "#addBook/400/invalidIsbn")
    void parameterizedRejectsInvalidIsbn(String isbn) {
        Status expected = broken("breakAllInvalidIsbn") ? Status.CREATED : Status.BAD_REQUEST;
        assertEquals(expected, new Library().addBook(isbn, "Effective Java"));
    }

    @RepeatedTest(3)
    @ForRequirement(id = "#addBook/409")
    void repeatedRejectsDuplicateIsbn() {
        Status expected = broken("breakRepeated") ? Status.CREATED : Status.CONFLICT;
        assertEquals(expected, libraryWithOneBook().addBook(ISBN, "Another Title"));
    }

    @TestFactory
    @ForRequirement(id = "#addBook/201/validIsbn")
    Stream<DynamicTest> dynamicAddsBooksWithValidIsbn() {
        Status expected = broken("breakDynamic") ? Status.BAD_REQUEST : Status.CREATED;
        return Stream.of("9780134685991", "9780000000001").map(isbn ->
            dynamicTest(isbn, () -> assertEquals(expected, new Library().addBook(isbn, "Title"))));
    }

    @Test
    @ForRequirement(id = "#listBooks/500")
    void annotatedWithRequirementMissingFromSpecification() {
        assertTrue(new Library().listBooks().isEmpty());
    }

    @Nested
    @Tag("deletion")
    class Deletion {
        @Test
        @ForRequirement(id = "#deleteBook/204")
        void nestedDeletesExistingBook() {
            assertEquals(Status.NO_CONTENT, libraryWithOneBook().deleteBook(ISBN));
        }

        @Test
        @ForRequirement(id = "#deleteBook/404")
        void nestedDeletingUnknownBookIsNotFound() {
            assertEquals(Status.NOT_FOUND, new Library().deleteBook(ISBN));
        }
    }
}
