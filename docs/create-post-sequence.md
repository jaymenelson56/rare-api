# Sequence Diagram — User Creates a New Post

The flow has two phases: **form setup** (component mount) and **form submission** (button click onward).

```mermaid
sequenceDiagram
    actor User
    participant PC  as PostCreate (component)
    participant CM  as CategoryManager
    participant PM  as PostManager
    participant LS  as localStorage
    participant URLRouter as Django URL Router
    participant TokenAuth  as DRF TokenAuthentication
    participant CV  as category_list view
    participant PV  as post_list view
    participant IV  as upload_post_image view
    participant ORM as Django ORM
    participant FS  as Local Filesystem
    participant DB  as PostgreSQL

    %% ─────────────────────────────────────────────────────────
    %% PHASE 1 — Component mount: populate the category dropdown
    %% ─────────────────────────────────────────────────────────
    Note over PC,DB: Phase 1 — Component mounts, category dropdown is populated

    PC->>CM: getCategories()
    CM->>LS: getItem("auth_token")
    LS-->>CM: "abc123"
    CM->>URLRouter: GET /categories<br/>Authorization: Token abc123
    URLRouter->>TokenAuth: authenticate(request)
    TokenAuth->>DB: SELECT * FROM authtoken_token WHERE key = 'abc123'
    DB-->>TokenAuth: token row → RareUser id=7
    TokenAuth-->>URLRouter: request.user = RareUser(id=7, is_staff=false)
    URLRouter->>CV: category_list(request)
    CV->>ORM: Category.objects.all()
    ORM->>DB: SELECT id, label FROM rareapi_category
    DB-->>ORM: category rows
    ORM-->>CV: Category queryset
    CV-->>CM: 200 OK  [{"id":1,"label":"Tech"}, {"id":2,"label":"News"}, ...]
    CM-->>PC: categories[]
    PC->>PC: setCategories(categories) — dropdown rendered

    %% ─────────────────────────────────────────────────────────
    %% PHASE 2 — User fills in the form and clicks Save
    %% ─────────────────────────────────────────────────────────
    Note over User,DB: Phase 2 — User completes the form and submits

    User->>PC: fills in Title, selects Category, writes Content,<br/>(optionally) picks an image file
    User->>PC: clicks "Save" button (form onSubmit)
    PC->>PC: handleSave(e) — e.preventDefault()

    PC->>PM: createPost({ title, category_id, content })
    PM->>LS: getItem("auth_token")
    LS-->>PM: "abc123"
    PM->>URLRouter: POST /posts<br/>Authorization: Token abc123<br/>Content-Type: application/json<br/>Body: { "title": "...", "category_id": 2, "content": "..." }

    URLRouter->>TokenAuth: authenticate(request)
    TokenAuth->>DB: SELECT * FROM authtoken_token WHERE key = 'abc123'
    DB-->>TokenAuth: token row → RareUser id=7
    TokenAuth-->>URLRouter: request.user = RareUser(id=7, is_staff=false)

    URLRouter->>PV: post_list(request)  [POST branch]

    PV->>ORM: Category.objects.get(pk=2)
    ORM->>DB: SELECT * FROM rareapi_category WHERE id = 2
    DB-->>ORM: Category(id=2, label="News")
    ORM-->>PV: category object

    PV->>ORM: Post.objects.create(user=RareUser#7, category=Category#2,<br/>title, content, publication_date=today,<br/>approved=request.user.is_staff → False)
    ORM->>DB: INSERT INTO rareapi_post<br/>(user_id, category_id, title, content,<br/>image_url, publication_date, approved)<br/>VALUES (7, 2, '...', '...', '', today, false)
    DB-->>ORM: Post(id=42) — post enters the moderation queue

    Note over PV: PostDetailSerializer builds the response.<br/>It queries post_tags to include any tags.
    PV->>DB: SELECT * FROM rareapi_posttag<br/>JOIN rareapi_tag ON tag_id = rareapi_tag.id<br/>WHERE post_id = 42
    DB-->>PV: [] (no tags on a brand-new post)

    PV-->>PM: 201 Created  { "id": 42, "title": "...", "approved": false, "user": {...}, "category": {...}, "tags": [] }
    PM-->>PC: post object (id=42)

    %% ─────────────────────────────────────────────────────────
    %% PHASE 3 — Optional image upload, then navigate away
    %% ─────────────────────────────────────────────────────────
    Note over PC,DB: Phase 3 — Optional image upload

    alt User selected an image file
        PC->>PM: uploadPostImage(42, FormData{ image: <file> })
        PM->>LS: getItem("auth_token")
        LS-->>PM: "abc123"
        PM->>URLRouter: PUT /posts/42/image<br/>Authorization: Token abc123<br/>Content-Type: multipart/form-data<br/>Body: FormData{ image: <file> }

        URLRouter->>TokenAuth: authenticate(request)
        TokenAuth->>DB: SELECT * FROM authtoken_token WHERE key = 'abc123'
        DB-->>TokenAuth: RareUser id=7
        TokenAuth-->>URLRouter: request.user = RareUser(id=7)

        URLRouter->>IV: upload_post_image(request, pk=42)
        IV->>ORM: Post.objects.get(pk=42)
        ORM->>DB: SELECT * FROM rareapi_post WHERE id = 42
        DB-->>ORM: Post(id=42, user_id=7)
        ORM-->>IV: post object
        IV->>IV: assert post.user == request.user  ✓
        IV->>FS: write chunks to MEDIA_ROOT/post_images/post_42_<filename>
        FS-->>IV: file saved
        IV->>IV: absolute_url = request.build_absolute_uri("/media/post_images/post_42_...")
        IV->>ORM: post.image_url = absolute_url; post.save()
        ORM->>DB: UPDATE rareapi_post SET image_url = 'http://localhost:8000/media/...' WHERE id = 42
        DB-->>ORM: OK
        IV-->>PM: 200 OK  { "image_url": "http://localhost:8000/media/..." }
        PM-->>PC: response
        PC->>PC: navigate("/posts/42")
    else No image selected
        PC->>PC: navigate("/posts/42")
    end
```

## Notes

- **Token validation** happens on every request via DRF's `TokenAuthentication` middleware before the view is reached. It always issues a `SELECT` against `authtoken_token`.
- **`approved = request.user.is_staff`** — because the user in this flow is a regular author (`is_staff=False`), the post is saved with `approved=False` and enters the moderation queue. It is not publicly visible until an admin approves it via `PUT /posts/42/approve`.
- **Image upload is a separate round-trip** (`PUT /posts/{id}/image`). The post row already exists in the database when the image request fires; the upload view writes the file to `MEDIA_ROOT/post_images/` and then does a second `UPDATE` to store the resolved URL in `post.image_url`.
- **Category fetch on mount** is required before the form is interactive. If it is still in-flight when the user submits, `categoryRef.current.value` will be empty and the `required` attribute on the `<select>` will block submission.
