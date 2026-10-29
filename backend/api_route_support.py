"""Explicit shared imports used by the focused API route modules."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import MetaData, Table, desc, func, or_
from sqlalchemy.orm import Session

import auth
import erp_service
import models
import schemas
from audit import request_ip, write_audit_log
from database import get_db
from api_helpers import can_view_procurement, employee_branch_ids, employee_name, scope_sales_query
