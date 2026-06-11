from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.role import Role
from app.schemas.tenant import TenantResponse, TenantRegistrationRequest, TenantUpdate
from app.core.security import hash_password
from app.api.dependencies import get_current_user, AdminOnly

router = APIRouter()

@router.post("/register", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(
    data: TenantRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Registra un nuevo Tenant y crea a su usuario administrador.
    Este endpoint suele ser público para que los talleres se auto-registren (SaaS).
    """
    # Validar si el email ya existe
    res = await db.execute(select(User).where(User.email == data.admin_email))
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email del administrador ya está en uso."
        )

    # 1. Crear el Tenant
    new_tenant = Tenant(
        name=data.tenant_name,
        tax_id=data.tax_id,
        is_active=True
    )
    db.add(new_tenant)
    await db.flush() # Para obtener el ID del tenant

    # 2. Obtener el rol de admin de taller (workshop_owner o tenant_admin)
    res_role = await db.execute(select(Role).where(Role.name == "workshop_owner"))
    role_owner = res_role.scalar_one_or_none()
    if not role_owner:
        raise HTTPException(status_code=500, detail="Rol workshop_owner no configurado en el sistema.")

    # 3. Crear el usuario Administrador
    new_admin = User(
        email=data.admin_email,
        password_hash=hash_password(data.admin_password),
        full_name=data.admin_full_name,
        tenant_id=new_tenant.id,
        roles=[role_owner]
    )
    db.add(new_admin)
    
    # Hacer commit de toda la transacción
    await db.commit()
    await db.refresh(new_tenant)

    return new_tenant

@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Devuelve los datos del Tenant del usuario actual."""
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a ningún Tenant.")
        
    res = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
        
    return tenant

# ── Endpoints de Gestión para el SuperAdmin ───────────────────

@router.get("/", response_model=list[TenantResponse])
async def list_tenants(
    admin: AdminOnly,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """Lista todas las empresas/talleres registradas en el sistema (Solo SuperAdmin)."""
    from sqlalchemy.orm import selectinload
    res = await db.execute(select(Tenant).options(selectinload(Tenant.workshops)).offset(skip).limit(limit))
    tenants = res.scalars().all()
    
    # Si el Tenant no tiene NIT, intentar sacar el NIT de su primer taller
    for t in tenants:
        if not t.tax_id and t.workshops:
            for w in t.workshops:
                if w.tax_id:
                    t.tax_id = w.tax_id
                    break
    
    return tenants

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    admin: AdminOnly,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene los detalles de una empresa específica (Solo SuperAdmin)."""
    res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    return tenant

@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    admin: AdminOnly,
    db: AsyncSession = Depends(get_db)
):
    """Modifica o suspende a una empresa entera (Solo SuperAdmin)."""
    res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)
        
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant
