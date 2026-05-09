{{- define "devault.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "devault.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name (include "devault.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "devault.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "devault.labels" -}}
helm.sh/chart: {{ include "devault.chart" . }}
{{ include "devault.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}

{{- define "devault.selectorLabels" -}}
app.kubernetes.io/name: {{ include "devault.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "devault.postgresHost" -}}
{{ include "devault.fullname" . }}-postgres
{{- end }}

{{- define "devault.redisHost" -}}
{{ include "devault.fullname" . }}-redis
{{- end }}

{{- define "devault.minioHost" -}}
{{ include "devault.fullname" . }}-minio
{{- end }}

{{- define "devault.databaseUrl" -}}
{{- $u := .Values.postgresql.auth.username }}
{{- $p := .Values.postgresql.auth.password }}
{{- $db := .Values.postgresql.auth.database }}
{{- $h := include "devault.postgresHost" . }}
{{- printf "postgresql+psycopg://%s:%s@%s:5432/%s" $u $p $h $db }}
{{- end }}

{{- define "devault.effectiveDatabaseUrl" -}}
{{- if .Values.postgresql.enabled -}}
{{- include "devault.databaseUrl" . -}}
{{- else -}}
{{- required "Set postgresql.enabled=true or provide devault.databaseUrl" .Values.devault.databaseUrl -}}
{{- end -}}
{{- end }}
