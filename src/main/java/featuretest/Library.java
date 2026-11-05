package featuretest;

import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class Library {
    private final Map<String, Book> books = new ConcurrentHashMap<>();

    public Status addBook(String isbn, String title) {
        if (isbn == null || !isbn.matches("\\d{13}")) return Status.BAD_REQUEST;
        if (title == null || title.isBlank()) return Status.BAD_REQUEST;
        if (books.containsKey(isbn)) return Status.CONFLICT;
        books.put(isbn, new Book(isbn, title.strip()));
        return Status.CREATED;
    }

    public Optional<Book> getBook(String isbn) {
        return Optional.ofNullable(books.get(isbn));
    }

    public List<Book> listBooks() {
        return books.values().stream().sorted(Comparator.comparing(Book::title)).toList();
    }

    public Status deleteBook(String isbn) {
        return books.remove(isbn) == null ? Status.NOT_FOUND : Status.NO_CONTENT;
    }

    public String ping() {
        return "pong";
    }
}
