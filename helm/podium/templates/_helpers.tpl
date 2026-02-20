{{/*
Expand the name of the chart.
*/}}
{{- define "podium.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "podium.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "podium.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Resolve the image for a given service.
Priority: service-level repository > global repository. Tag same pattern.
Usage: include "podium.image" (dict "root" . "svc" .Values.gateway "name" "gateway")
*/}}
{{- define "podium.image" -}}
{{- $reg := .root.Values.image.registry -}}
{{- $repo := .svc.image.repository | default .root.Values.image.repository -}}
{{- $tag  := .svc.image.tag        | default .root.Values.image.tag -}}
{{ printf "%s/%s:%s" $reg $repo $tag }}
{{- end }}

{{/*
Common env — secret refs shared across all backend services.
*/}}
{{- define "podium.commonEnv" -}}
- name: NODE_ENV
  valueFrom:
    configMapKeyRef:
      name: {{ include "podium.fullname" . }}-config
      key: NODE_ENV
- name: PODIUM_PRODUCTION_URL
  valueFrom:
    configMapKeyRef:
      name: {{ include "podium.fullname" . }}-config
      key: PODIUM_PRODUCTION_URL
- name: PODIUM_JWT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ include "podium.fullname" . }}-secrets
      key: PODIUM_JWT_SECRET
- name: PODIUM_JWT_ALGORITHM
  valueFrom:
    configMapKeyRef:
      name: {{ include "podium.fullname" . }}-config
      key: PODIUM_JWT_ALGORITHM
- name: PODIUM_JWT_EXPIRE_MINUTES
  valueFrom:
    configMapKeyRef:
      name: {{ include "podium.fullname" . }}-config
      key: PODIUM_JWT_EXPIRE_MINUTES
- name: PODIUM_DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "podium.fullname" . }}-secrets
      key: PODIUM_DB_PASSWORD
- name: PODIUM_DATABASE_URL_RW
  valueFrom:
    configMapKeyRef:
      name: {{ include "podium.fullname" . }}-config
      key: PODIUM_DATABASE_URL_RW
- name: PODIUM_DATABASE_URL_RO
  valueFrom:
    configMapKeyRef:
      name: {{ include "podium.fullname" . }}-config
      key: PODIUM_DATABASE_URL_RO
- name: PODIUM_DATABASE_URL_R
  valueFrom:
    configMapKeyRef:
      name: {{ include "podium.fullname" . }}-config
      key: PODIUM_DATABASE_URL_R
- name: PODIUM_ACTIVE_EVENT_SERIES
  valueFrom:
    configMapKeyRef:
      name: {{ include "podium.fullname" . }}-config
      key: PODIUM_ACTIVE_EVENT_SERIES
- name: PODIUM_ENABLE_TEST_ENDPOINTS
  valueFrom:
    configMapKeyRef:
      name: {{ include "podium.fullname" . }}-config
      key: PODIUM_ENABLE_TEST_ENDPOINTS
{{- end }}
