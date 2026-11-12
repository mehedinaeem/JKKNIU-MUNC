from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Event
from accounts.permissions import EventManagementPermission
from accounts.roles import scope_queryset
from .serializers import EventQuerySerializer, EventSerializer


class PublicEventList(generics.ListAPIView):
    serializer_class = EventSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        query = EventQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        events = Event.objects.filter(status=Event.Status.PUBLISHED)
        if "event_type" in params:
            events = events.filter(event_type=params["event_type"])
        if "start_date_after" in params:
            events = events.filter(start_date__gte=params["start_date_after"])
        if "start_date_before" in params:
            events = events.filter(start_date__lte=params["start_date_before"])
        if params.get("search"):
            term = params["search"]
            events = events.filter(Q(title__icontains=term) | Q(short_description__icontains=term)
                                   | Q(description__icontains=term) | Q(venue__icontains=term))
        return events.order_by(params.get("ordering", "-start_date"), "-id")


class PublicEventDetail(generics.RetrieveAPIView):
    queryset = Event.objects.filter(status=Event.Status.PUBLISHED)
    serializer_class = EventSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"


class StaffEventCreate(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [EventManagementPermission]
    permission_model = "events.event"

    super_admin_create = True

    def get_queryset(self):
        return scope_queryset(Event.objects.all(), self.request.user, 'pk')

    def perform_create(self, serializer):
        if "organizer" not in serializer.validated_data:
            serializer.save(organizer=self.request.user)
        else:
            serializer.save()


class StaffEventDetail(generics.GenericAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [EventManagementPermission]
    permission_model = "events.event"

    def get_queryset(self):
        return scope_queryset(Event.objects.all(), self.request.user, 'pk')

    def get(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_object()).data)

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        from django.db.models.deletion import ProtectedError
        try:
            self.get_object().delete()
        except ProtectedError:
            return Response({'detail': 'Archive this event; published forms and submissions must be retained.'}, status=409)
        return Response(status=204)
