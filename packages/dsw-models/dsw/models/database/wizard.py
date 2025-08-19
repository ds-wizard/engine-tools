import datetime
import uuid

from sqlalchemy import DateTime, Uuid, String, Boolean, Integer, JSON, ARRAY, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.types import UserDefinedType


class Base(DeclarativeBase):
    pass


class ActionKey(Base):
    __tablename__ = 'action_key'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    identity: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    type: Mapped[str] = mapped_column(String, nullable=False)
    hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK


class Branch(Base):
    __tablename__ = 'branch'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    km_id: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    readme: Mapped[str] = mapped_column(String, nullable=False)
    license: Mapped[str] = mapped_column(String, nullable=False)
    previous_package_id: Mapped[str | None] = mapped_column(String, nullable=True)  # TODO: FK
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class BranchData(Base):
    __tablename__ = 'branch_data'

    branch_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    metamodel_version: Mapped[int] = mapped_column(Integer, nullable=False)
    events: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    squashed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    replies: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class Component(Base):
    __tablename__ = 'component'

    name: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[str] = mapped_column(String, nullable=False)
    built_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigAuthentication(Base):
    __tablename__ = 'config_authentication'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    default_role: Mapped[str] = mapped_column(String, nullable=False)
    internal_registration_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    internal_two_factor_auth_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    internal_two_factor_auth_code_length: Mapped[int] = mapped_column(Integer, nullable=False)
    internal_two_factor_auth_code_expiration: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigAuthenticationOpenID(Base):
    __tablename__ = 'config_authentication_openid'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    client_id: Mapped[str] = mapped_column(String, nullable=False)
    client_secret: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    style_icon: Mapped[str | None] = mapped_column(String, nullable=True)
    style_background: Mapped[str | None] = mapped_column(String, nullable=True)
    style_color: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigDashboardAndLoginScreen(Base):
    __tablename__ = 'config_dashboard_and_login_screen'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    dashboard_type: Mapped[str] = mapped_column(String, nullable=False)
    login_info: Mapped[str | None] = mapped_column(String, nullable=True)
    login_info_sidebar: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigDashboardAndLoginScreenAnnouncement(Base):
    __tablename__ = 'config_dashboard_and_login_screen_announcement'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, primary_key=True)  # TODO: FK
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False)  # TODO: enum
    login_screen: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dashboard: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigFeatures(Base):
    __tablename__ = 'config_features'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    ai_assistant_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tours_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigKnowledgeModel(Base):
    __tablename__ = 'config_knowledge_model'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    public_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    integration_config: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigKnowledgeModelPublicPackagePattern(Base):
    __tablename__ = 'config_knowledge_model_public_package_pattern'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[str | None] = mapped_column(String, nullable=True)
    km_id: Mapped[str | None] = mapped_column(String, nullable=True)
    min_version: Mapped[str | None] = mapped_column(String, nullable=True)
    max_version: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigLookAndFeel(Base):
    __tablename__ = 'config_look_and_feel'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    app_title: Mapped[str | None] = mapped_column(String, nullable=True)
    app_title_short: Mapped[str | None] = mapped_column(String, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String, nullable=True)
    illustrations_color: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigLookAndFeelCustomMenuLink(Base):
    __tablename__ = 'config_look_and_feel_custom_menu_link'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    new_window: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigMail(Base):
    __tablename__ = 'config_mail'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    config_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigOrganization(Base):
    __tablename__ = 'config_organization'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    affiliations: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigPrivacyAndSupport(Base):
    __tablename__ = 'config_privacy_and_support'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    privacy_url: Mapped[str | None] = mapped_column(String, nullable=True)
    terms_of_service_url: Mapped[str | None] = mapped_column(String, nullable=True)
    support_email: Mapped[str | None] = mapped_column(String, nullable=True)
    support_site_name: Mapped[str | None] = mapped_column(String, nullable=True)
    support_site_url: Mapped[str | None] = mapped_column(String, nullable=True)
    support_site_icon: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigQuestionnaire(Base):
    __tablename__ = 'config_questionnaire'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    visibility_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    visibility_default_value: Mapped[str] = mapped_column(String, nullable=False)
    sharing_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sharing_default_value: Mapped[str] = mapped_column(String, nullable=False)
    sharing_anonymous_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    creation: Mapped[str] = mapped_column(String, nullable=False)
    project_tagging_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    project_tagging_tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    summary_report: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback_token: Mapped[str] = mapped_column(String, nullable=False)
    feedback_owner: Mapped[str] = mapped_column(String, nullable=False)
    feedback_repo: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigRegistry(Base):
    __tablename__ = 'config_registry'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigSubmission(Base):
    __tablename__ = 'config_submission'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigSubmissionService(Base):
    __tablename__ = 'config_submission_service'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    props: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    request_method: Mapped[str] = mapped_column(String, nullable=False)
    request_url: Mapped[str] = mapped_column(String, nullable=False)
    request_multipart_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    request_multipart_file_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class ConfigSubmissionServiceRequestHeader(Base):
    __tablename__ = 'config_submission_service_request_header'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, primary_key=True)  # TODO: FK
    service_id: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)  # TODO: FK
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)


class ConfigSubmissionServiceSupportedFormat(Base):
    __tablename__ = 'config_submission_service_supported_format'

    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, primary_key=True)  # TODO: FK
    service_id: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)  # TODO: FK
    document_template_id: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)  # TODO: FK
    format_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, primary_key=True)  # TODO: FK


class Document(Base):
    __tablename__ = 'document'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    durability: Mapped[str] = mapped_column(String, nullable=False)
    questionnaire_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    questionnaire_event_uuid: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK ??
    questionnaire_replies_hash: Mapped[int] = mapped_column(BigInteger, nullable=False)
    document_template_id: Mapped[str] = mapped_column(String, nullable=False)  # TODO: FK
    format_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK
    retrieved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    file_name: Mapped[str | None] = mapped_column(String, nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    worker_log: Mapped[str | None] = mapped_column(String, nullable=True)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class DocumentTemplate(Base):
    __tablename__ = 'document_template'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    template_id: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    metamodel_version: Mapped[int] = mapped_column(Integer, nullable=False)  # TODO: sem_ver_2_tuple
    description: Mapped[str] = mapped_column(String, nullable=False)
    readme: Mapped[str] = mapped_column(String, nullable=False)
    license: Mapped[str] = mapped_column(String, nullable=False)
    allowed_packages: Mapped[dict] = mapped_column(JSON, nullable=False)  # TODO: why different than config public KM?
    phase: Mapped[str] = mapped_column(String, nullable=False)
    non_editable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class DocumentTemplateAsset(Base):
    __tablename__ = 'document_template_asset'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    document_template_id: Mapped[str] = mapped_column(String, nullable=False)  # TODO: FK, not PK??
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class DocumentTemplateDraftData(Base):
    __tablename__ = 'document_template_draft_data'

    document_template_id: Mapped[str] = mapped_column(String, primary_key=True)  # TODO: FK, not PK??
    questionnaire_uuid: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK
    branch_uuid: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK ???
    format_uuid: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK ???
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class DocumentTemplateFile(Base):
    __tablename__ = 'document_template_file'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    document_template_id: Mapped[str] = mapped_column(String, nullable=False)  # TODO: FK, not PK??
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class DocumentTemplateFormat(Base):
    __tablename__ = 'document_template_format'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    document_template_id: Mapped[str] = mapped_column(String, primary_key=True)  # TODO: FK
    name: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class DocumentTemplateFormatStep(Base):
    __tablename__ = 'document_template_format_step'

    document_template_id: Mapped[str] = mapped_column(String, primary_key=True)  # TODO: FK
    format_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    options: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class Feedback(Base):
    __tablename__ = 'feedback'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    issue_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    question_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    package_id: Mapped[str] = mapped_column(String, nullable=False)  # TODO: FK
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK


class InstanceConfigMail(Base):
    __tablename__ = 'instance_config_mail'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String, nullable=True)
    sender_email: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_host: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_security: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_username: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_password: Mapped[str | None] = mapped_column(String, nullable=True)
    rate_limit_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_limit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timeout: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aws_access_key_id: Mapped[str | None] = mapped_column(String, nullable=True)
    aws_secret_access_key: Mapped[str | None] = mapped_column(String, nullable=True)
    aws_region: Mapped[str | None] = mapped_column(String, nullable=True)


class KnowledgeModelCache(Base):
    __tablename__ = 'knowledge_model_cache'

    package_id: Mapped[str] = mapped_column(String, primary_key=True)  # TODO: FK
    tag_uuids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), nullable=False)  # TODO: why text[] ???
    knowledge_model: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class KnowledgeModelMigration(Base):
    __tablename__ = 'knowledge_model_migration'

    branch_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    metamodel_version: Mapped[int] = mapped_column(Integer, nullable=False)
    migration_state: Mapped[dict] = mapped_column(JSON, nullable=False)
    branch_previous_package_id: Mapped[str] = mapped_column(String, nullable=False)  # TODO: FK
    target_package_id: Mapped[str] = mapped_column(String, nullable=False)  # TODO: FK
    branch_events: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    target_package_events: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    result_events: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    current_knowledge_model: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class KnowledgeModelSecret(Base):
    __tablename__ = 'knowledge_model_secret'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class Locale(Base):
    __tablename__ = 'locale'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    locale_id: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    license: Mapped[str] = mapped_column(String, nullable=False)
    readme: Mapped[str] = mapped_column(String, nullable=False)
    recommended_app_version: Mapped[str] = mapped_column(String, nullable=False)
    default_locale: Mapped[bool] = mapped_column(Boolean, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class Migration(Base):
    __tablename__ = 'migration'

    number: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class Package(Base):
    __tablename__ = 'package'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    km_id: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    metamodel_version: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    readme: Mapped[str] = mapped_column(String, nullable=False)
    license: Mapped[str] = mapped_column(String, nullable=False)
    previous_package_id: Mapped[str | None] = mapped_column(String, nullable=True)  # TODO: FK
    fork_of_package_id: Mapped[str | None] = mapped_column(String, nullable=True)  # TODO: FK ???
    merge_checkpoint_package_id: Mapped[str | None] = mapped_column(String, nullable=True)  # TODO: FK ???
    events: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    phase: Mapped[str] = mapped_column(String, nullable=False)
    non_editable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class PersistentCommand(Base):
    __tablename__ = 'persistent_command'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    state: Mapped[str] = mapped_column(String, nullable=False)
    component: Mapped[str] = mapped_column(String, nullable=False)
    function: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    last_error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    internal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    destination: Mapped[str | None] = mapped_column(String, nullable=True)
    last_trace_uuid: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK


class Prefab(Base):
    __tablename__ = 'prefab'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class Questionnaire(Base):
    __tablename__ = 'questionnaire'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    project_tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    visibility: Mapped[str] = mapped_column(String, nullable=False)
    sharing: Mapped[str] = mapped_column(String, nullable=False)
    package_id: Mapped[str] = mapped_column(String, nullable=False)  # TODO: FK
    selected_question_tag_uuids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), nullable=False)
    document_template_id: Mapped[str | None] = mapped_column(String, nullable=True)  # TODO: FK
    format_uuid: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK
    is_template: Mapped[bool] = mapped_column(Boolean, nullable=False)
    squashed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class QuestionnaireAction(Base):
    __tablename__ = 'questionnaire_action'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    action_id: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    metamodel_version: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    readme: Mapped[str] = mapped_column(String, nullable=False)
    license: Mapped[str] = mapped_column(String, nullable=False)
    allowed_packages: Mapped[dict] = mapped_column(JSON, nullable=False)  # TODO: why different than config public KM?
    url: Mapped[str] = mapped_column(String, nullable=False)  # TODO: why nullable???
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class QuestionnaireComment(Base):
    __tablename__ = 'questionnaire_comment'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    text: Mapped[str] = mapped_column(String, nullable=False)
    comment_thread_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK ???
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class QuestionnaireCommentThread(Base):
    __tablename__ = 'questionnaire_comment_thread'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    path: Mapped[str] = mapped_column(String, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    private: Mapped[bool] = mapped_column(Boolean, nullable=False)
    questionnaire_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK
    notification_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK ???
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class QuestionnaireEvent(Base):
    __tablename__ = 'questionnaire_event'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)  # TODO: enum
    path: Mapped[str | None] = mapped_column(String, nullable=True)
    value_type: Mapped[str | None] = mapped_column(String, nullable=True)  # TODO: enum
    value: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    value_id: Mapped[str | None] = mapped_column(String, nullable=True)
    value_raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    questionnaire_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class QuestionnaireFile(Base):
    __tablename__ = 'questionnaire_file'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    questionnaire_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class QuestionnaireImporter(Base):
    __tablename__ = 'questionnaire_importer'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    importer_id: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    metamodel_version: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    readme: Mapped[str] = mapped_column(String, nullable=False)
    license: Mapped[str] = mapped_column(String, nullable=False)
    allowed_packages: Mapped[dict] = mapped_column(JSON, nullable=False)  # TODO: why different than config public KM?
    url: Mapped[str] = mapped_column(String, nullable=False)  # TODO: why nullable???
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class QuestionnaireMigration(Base):
    __tablename__ = 'questionnaire_migration'

    old_questionnaire_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    new_questionnaire_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    resolved_question_uuids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK  (not PK??)


class QuestionnairePermGroup(Base):
    __tablename__ = 'questionnaire_perm_group'

    questionnaire_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    user_group_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    perms: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class QuestionnairePermUser(Base):
    __tablename__ = 'questionnaire_perm_user'

    questionnaire_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    user_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    perms: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class QuestionnaireVersion(Base):
    __tablename__ = 'questionnaire_version'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    event_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    questionnaire_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class Submission(Base):
    __tablename__ = 'submission'  # TODO: document_submission???

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    state: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    returned_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    service_id: Mapped[str] = mapped_column(String, nullable=False)  # TODO: FK ???
    document_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK (optional???)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # TODO: FK
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)  # nullable???
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class Tenant(Base):
    __tablename__ = 'tenant'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    server_domain: Mapped[str] = mapped_column(String, nullable=False)
    client_url: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class TenantLimitBundle(Base):
    __tablename__ = 'tenant_limit_bundle'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK?? tenant_uuid???
    users: Mapped[int] = mapped_column(Integer, nullable=False)
    active_users: Mapped[int] = mapped_column(Integer, nullable=False)
    knowledge_models: Mapped[int] = mapped_column(Integer, nullable=False)
    branches: Mapped[int] = mapped_column(Integer, nullable=False)
    document_templates: Mapped[int] = mapped_column(Integer, nullable=False)
    document_template_drafts: Mapped[int] = mapped_column(Integer, nullable=False)
    questionnaires: Mapped[int] = mapped_column(Integer, nullable=False)
    documents: Mapped[int] = mapped_column(Integer, nullable=False)
    locales: Mapped[int] = mapped_column(Integer, nullable=False)
    storage: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


class UserEntity(Base):
    __tablename__ = 'user_entity'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    affiliation: Mapped[str | None] = mapped_column(String, nullable=True)
    sources: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    permissions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    machine: Mapped[bool] = mapped_column(Boolean, nullable=False)
    locale: Mapped[str | None] = mapped_column(String, nullable=True)  # TODO: FK???
    last_visited_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)  # nullable???
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class UserEntitySubmissionProp(Base):
    __tablename__ = 'user_entity_submission_prop'

    user_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    service_id: Mapped[str] = mapped_column(String, primary_key=True)  # TODO: FK
    values: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class UserGroup(Base):
    __tablename__ = 'user_group'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    private: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class UserGroupMembership(Base):
    __tablename__ = 'user_group_membership'

    user_group_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    user_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class UserToken(Base):
    __tablename__ = 'user_token'

    uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)  # TODO: FK
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    user_agent: Mapped[str] = mapped_column(String, nullable=False)
    session_state: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK


class UserTour(Base):
    __tablename__ = 'user_tour'

    user_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
    tour_id: Mapped[str] = mapped_column(String, primary_key=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    tenant_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # TODO: FK
