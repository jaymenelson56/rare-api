import os
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rareapi.models import Post, Tag, PostTag, Category
from rareapi.serializers import PostDetailSerializer, PostListSerializer, CategorySerializer, TagSerializer


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def post_list(request):
    """List approved posts (GET) or create a new post (POST).

    Domain rule: on POST, the post's `approved` flag is set to the creator's
    `is_staff` value. Admins' posts auto-publish; regular authors' posts enter
    the moderation queue (visible via /unapprovedposts to admins only).
    """
    if request.method == 'POST':
        try:
            category = Category.objects.get(pk=request.data.get('category_id'))
        except Category.DoesNotExist:
            return Response({'error': 'Invalid category'}, status=400)

        post = Post.objects.create(
            user=request.user,
            category=category,
            title=request.data.get('title'),
            content=request.data.get('content'),
            image_url=request.data.get('image_url', ''),
            publication_date=timezone.now().date(),
            approved=request.user.is_staff,  # see docstring — admins auto-publish
        )
        return Response(PostDetailSerializer(post).data, status=201)

    posts = (
        Post.objects
        .select_related('user', 'category')
        .filter(approved=True, publication_date__lte=timezone.now().date())
        .order_by('-publication_date')
    )
    return Response(PostListSerializer(posts, many=True).data)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def post_detail(request, pk):
    try:
        post = Post.objects.select_related('user', 'category').get(pk=pk)
    except Post.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'DELETE':
        if post.user != request.user and not request.user.is_staff:
            return Response({'error': 'Forbidden'}, status=403)
        post.delete()
        return Response(status=204)

    if request.method == 'PUT':
        if post.user != request.user:
            return Response({'error': 'Forbidden'}, status=403)

        try:
            category = Category.objects.get(pk=request.data.get('category_id'))
        except Category.DoesNotExist:
            return Response({'error': 'Invalid category'}, status=400)

        post.title = request.data.get('title', post.title)
        post.content = request.data.get('content', post.content)
        post.image_url = request.data.get('image_url', post.image_url)
        post.category = category
        post.save()

    return Response(PostDetailSerializer(post).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_post_list(request):
    posts = (
        Post.objects
        .select_related('user', 'category')
        .filter(user=request.user)
        .order_by('-publication_date', '-id')
    )
    return Response(PostListSerializer(posts, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_post_list(request, user_id):
    posts = (
        Post.objects
        .select_related('user', 'category')
        .filter(user_id=user_id, approved=True)
        .order_by('-publication_date', '-id')
    )
    return Response(PostListSerializer(posts, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscribed_posts(request):
    subscribed_author_ids = request.user.subscriptions.filter(ended_on__isnull=True).values_list('author_id', flat=True)
    posts = (
        Post.objects
        .select_related('user', 'category')
        .filter(
            user_id__in=subscribed_author_ids,
            approved=True,
            publication_date__lte=timezone.now().date()
        )
        .order_by('-publication_date')
    )
    return Response(PostListSerializer(posts, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unapproved_post_list(request):
    if not request.user.is_staff:
        return Response({'error': 'Forbidden'}, status=403)

    posts = (
        Post.objects
        .select_related('user', 'category')
        .filter(approved=False)
        .order_by('-publication_date', '-id')
    )
    return Response(PostListSerializer(posts, many=True).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def approve_post(request, pk):
    if not request.user.is_staff:
        return Response({'error': 'Forbidden'}, status=403)

    try:
        post = Post.objects.select_related('user', 'category').get(pk=pk)
    except Post.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    post.approved = True
    post.save()
    return Response(PostDetailSerializer(post).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def unapprove_post(request, pk):
    if not request.user.is_staff:
        return Response({'error': 'Forbidden'}, status=403)

    try:
        post = Post.objects.select_related('user', 'category').get(pk=pk)
    except Post.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    post.approved = False
    post.save()
    return Response(PostDetailSerializer(post).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def approved_post_list(request):
    if not request.user.is_staff:
        return Response({'error': 'Forbidden'}, status=403)

    posts = (
        Post.objects
        .select_related('user', 'category')
        .filter(approved=True)
        .order_by('-publication_date', '-id')
    )
    return Response(PostListSerializer(posts, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def category_post_list(request, category_id):
    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    posts = (
        Post.objects
        .select_related('user', 'category')
        .filter(category=category, approved=True, publication_date__lte=timezone.now().date())
        .order_by('-publication_date')
    )
    return Response({
        'category': CategorySerializer(category).data,
        'posts': PostListSerializer(posts, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tag_post_list(request, tag_id):
    try:
        tag = Tag.objects.get(pk=tag_id)
    except Tag.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    posts = (
        Post.objects
        .select_related('user', 'category')
        .filter(post_tags__tag=tag, approved=True, publication_date__lte=timezone.now().date())
        .order_by('-publication_date')
    )
    return Response({
        'tag': TagSerializer(tag).data,
        'posts': PostListSerializer(posts, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_posts(request):
    query = request.query_params.get('q', '').strip()
    author = request.query_params.get('author', '').strip()

    if not query and not author:
        return Response([])

    posts = (
        Post.objects
        .select_related('user', 'category')
        .filter(approved=True, publication_date__lte=timezone.now().date())
    )
    if query:
        posts = posts.filter(title__icontains=query)
    if author:
        posts = posts.filter(user__username__icontains=author)

    return Response(PostListSerializer(posts.order_by('-publication_date'), many=True).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def upload_post_image(request, pk):
    try:
        post = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if post.user != request.user:
        return Response({'error': 'Forbidden'}, status=403)

    if 'image' not in request.FILES:
        return Response({'error': 'No image provided'}, status=400)

    image = request.FILES['image']
    filename = f"post_{pk}_{image.name}"
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'post_images')
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    with open(filepath, 'wb+') as dest:
        for chunk in image.chunks():
            dest.write(chunk)

    relative_url = f"{settings.MEDIA_URL}post_images/{filename}"
    absolute_url = request.build_absolute_uri(relative_url)

    post.image_url = absolute_url
    post.save()

    return Response({'image_url': absolute_url})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def post_tags(request, pk):
    try:
        post = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if post.user != request.user:
        return Response({'error': 'Forbidden'}, status=403)

    tag_ids = request.data.get('tag_ids', [])
    PostTag.objects.filter(post=post).delete()
    for tag_id in tag_ids:
        try:
            tag = Tag.objects.get(pk=tag_id)
            PostTag.objects.create(post=post, tag=tag)
        except Tag.DoesNotExist:
            pass

    return Response(PostDetailSerializer(post).data)
