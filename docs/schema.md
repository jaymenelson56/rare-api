# Rare — Database Schema

```mermaid
erDiagram

    RareUser {
        int id PK
        string username
        string password
        string email
        string first_name
        string last_name
        bool is_staff
        bool is_active
        date date_joined
        string bio
        string profile_image_url
        date created_on
    }

    Category {
        int id PK
        string label
    }

    Tag {
        int id PK
        string label
    }

    Reaction {
        int id PK
        string label
        string image_url
    }

    Post {
        int id PK
        int user_id FK
        int category_id FK
        string title
        date publication_date
        string image_url
        text content
        bool approved
    }

    Comment {
        int id PK
        int post_id FK
        int author_id FK
        string subject
        text content
        datetime created_on
    }

    Subscription {
        int id PK
        int follower_id FK
        int author_id FK
        date created_on
        datetime ended_on "nullable"
    }

    PostTag {
        int id PK
        int post_id FK
        int tag_id FK
    }

    PostReaction {
        int id PK
        int user_id FK
        int post_id FK
        int reaction_id FK
    }

    DemotionQueue {
        int id PK
        string action
        int admin_id FK
        int approver_one_id FK
    }

    RareUser ||--o{ Post : "writes"
    Category ||--o{ Post : "classifies"
    Post ||--o{ Comment : "has"
    RareUser ||--o{ Comment : "writes"
    RareUser ||--o{ Subscription : "follows (follower)"
    RareUser ||--o{ Subscription : "is followed by (author)"
    Post ||--o{ PostTag : "has"
    Tag ||--o{ PostTag : "applied via"
    Post ||--o{ PostReaction : "receives"
    RareUser ||--o{ PostReaction : "reacts"
    Reaction ||--o{ PostReaction : "used in"
    RareUser ||--o{ DemotionQueue : "initiates (admin)"
    RareUser ||--o{ DemotionQueue : "approves (approver_one)"
```

## Notes

- `RareUser` extends Django's `AbstractUser` — the fields `username` through `date_joined` are inherited; `bio`, `profile_image_url`, and `created_on` are custom additions.
- `Post.approved` defaults to `false` for regular users; admin-authored posts are auto-approved by the API layer.
- `Subscription.ended_on` is nullable — a `NULL` value means the subscription is currently active; a timestamp means it was cancelled.
- `DemotionQueue` enforces `unique_together(action, admin, approver_one)` to prevent duplicate approval votes.
- `PostTag` and `PostReaction` are explicit join tables rather than Django `ManyToManyField` so the API can address them directly.
