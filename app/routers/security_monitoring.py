"""
📊 Security Dashboard API
API pour le monitoring de sécurité en temps réel

Créé : 20 janvier 2026
Objectif : Jalon 3.2 - Monitoring Sécurité
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse
import json

from app.core.secure_logging import secure_logger
from app.core.security import get_current_user, require_admin
from app.middleware.auth import get_current_user_from_token

router = APIRouter(prefix="/api/v1/security", tags=["security-monitoring"])


@router.get("/dashboard", response_class=HTMLResponse)
async def security_dashboard():
    """Page HTML du dashboard de sécurité."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AindusDB Security Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .card { @apply bg-white rounded-lg shadow-md p-6 mb-4; }
            .metric { @apply text-3xl font-bold text-blue-600; }
            .alert-high { @apply bg-red-100 border-red-400 text-red-700; }
            .alert-medium { @apply bg-yellow-100 border-yellow-400 text-yellow-700; }
            .alert-low { @apply bg-green-100 border-green-400 text-green-700; }
        </style>
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto p-4">
            <h1 class="text-3xl font-bold mb-6">🛡️ Security Dashboard</h1>
            
            <!-- Metrics Cards -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div class="card">
                    <h3 class="text-gray-600">Total Events (24h)</h3>
                    <div class="metric" id="totalEvents">-</div>
                </div>
                <div class="card">
                    <h3 class="text-gray-600">High Risk Events</h3>
                    <div class="metric text-red-600" id="highRiskEvents">-</div>
                </div>
                <div class="card">
                    <h3 class="text-gray-600">Failed Logins (1h)</h3>
                    <div class="metric text-yellow-600" id="failedLogins">-</div>
                </div>
                <div class="card">
                    <h3 class="text-gray-600">Blocked IPs</h3>
                    <div class="metric text-orange-600" id="blockedIPs">-</div>
                </div>
            </div>
            
            <!-- Charts -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div class="card">
                    <h3 class="text-xl font-semibold mb-4">Events by Type</h3>
                    <canvas id="eventTypeChart"></canvas>
                </div>
                <div class="card">
                    <h3 class="text-xl font-semibold mb-4">Risk Score Trend</h3>
                    <canvas id="riskTrendChart"></canvas>
                </div>
            </div>
            
            <!-- Recent Events -->
            <div class="card">
                <h3 class="text-xl font-semibold mb-4">Recent Security Events</h3>
                <div id="recentEvents" class="space-y-2">
                    <div class="text-gray-500">Loading...</div>
                </div>
            </div>
            
            <!-- Suspicious IPs -->
            <div class="card">
                <h3 class="text-xl font-semibold mb-4">Top Suspicious IPs</h3>
                <div id="suspiciousIPs" class="overflow-x-auto">
                    <table class="min-w-full table-auto">
                        <thead>
                            <tr class="bg-gray-200">
                                <th class="px-4 py-2">IP Address</th>
                                <th class="px-4 py-2">Events Count</th>
                                <th class="px-4 py-2">Avg Risk Score</th>
                                <th class="px-4 py-2">Last Seen</th>
                            </tr>
                        </thead>
                        <tbody id="suspiciousIPsBody">
                            <tr><td colspan="4" class="text-center text-gray-500">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <script>
            // Fetch data from API
            async function fetchSecurityData() {
                try {
                    const response = await fetch('/api/v1/security/stats');
                    const data = await response.json();
                    
                    // Update metrics
                    document.getElementById('totalEvents').textContent = data.total_events.toLocaleString();
                    document.getElementById('highRiskEvents').textContent = data.high_risk_events.toLocaleString();
                    document.getElementById('failedLogins').textContent = data.failed_logins_1h.toLocaleString();
                    document.getElementById('blockedIPs').textContent = data.blocked_ips_count.toLocaleString();
                    
                    // Update charts
                    updateEventTypeChart(data.events_by_type);
                    updateRiskTrendChart(data.risk_trend);
                    
                    // Update recent events
                    updateRecentEvents(data.recent_events);
                    
                    // Update suspicious IPs
                    updateSuspiciousIPs(data.suspicious_ips);
                    
                } catch (error) {
                    console.error('Error fetching security data:', error);
                }
            }
            
            function updateEventTypeChart(data) {
                const ctx = document.getElementById('eventTypeChart').getContext('2d');
                new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(data),
                        datasets: [{
                            data: Object.values(data),
                            backgroundColor: [
                                '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
                                '#8B5CF6', '#EC4899', '#6B7280', '#059669'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { position: 'bottom' }
                        }
                    }
                });
            }
            
            function updateRiskTrendChart(data) {
                const ctx = document.getElementById('riskTrendChart').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: 'Average Risk Score',
                            data: data.values,
                            borderColor: '#EF4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: { beginAtZero: true, max: 10 }
                        }
                    }
                });
            }
            
            function updateRecentEvents(events) {
                const container = document.getElementById('recentEvents');
                container.innerHTML = events.map(event => {
                    const riskClass = event.risk_score >= 7 ? 'alert-high' : 
                                    event.risk_score >= 4 ? 'alert-medium' : 'alert-low';
                    const timeAgo = new Date(event.timestamp).toLocaleString();
                    
                    return `
                        <div class="border rounded p-3 ${riskClass}">
                            <div class="flex justify-between">
                                <span class="font-semibold">[${event.event_type}] ${event.message}</span>
                                <span class="text-sm">${timeAgo}</span>
                            </div>
                            ${event.ip_address ? `<div class="text-sm mt-1">IP: ${event.ip_address}</div>` : ''}
                            ${event.risk_score > 0 ? `<div class="text-sm">Risk: ${event.risk_score}/10</div>` : ''}
                        </div>
                    `;
                }).join('');
            }
            
            function updateSuspiciousIPs(ips) {
                const tbody = document.getElementById('suspiciousIPsBody');
                tbody.innerHTML = ips.map(ip => `
                    <tr class="border-b">
                        <td class="px-4 py-2 font-mono">${ip.ip_address}</td>
                        <td class="px-4 py-2">${ip.count}</td>
                        <td class="px-4 py-2">
                            <span class="px-2 py-1 rounded text-sm ${
                                ip.avg_risk >= 7 ? 'bg-red-200 text-red-800' :
                                ip.avg_risk >= 4 ? 'bg-yellow-200 text-yellow-800' :
                                'bg-green-200 text-green-800'
                            }">
                                ${ip.avg_risk.toFixed(1)}
                            </span>
                        </td>
                        <td class="px-4 py-2">${new Date(ip.last_seen).toLocaleString()}</td>
                    </tr>
                `).join('');
            }
            
            // Auto-refresh every 30 seconds
            fetchSecurityData();
            setInterval(fetchSecurityData, 30000);
        </script>
    </body>
    </html>
    """


@router.get("/stats")
async def get_security_stats(
    days: int = Query(default=7, ge=1, le=30),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Obtenir les statistiques de sécurité."""
    # Vérifier les permissions
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Obtenir les stats de base
    stats = await secure_logger.get_security_stats(days)
    
    # Calculer les métriques supplémentaires
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    # Logins échoués (dernière heure)
    failed_logins = await secure_logger.search_logs(
        event_type="AUTH_FAILED",
        start_time=one_hour_ago,
        end_time=now
    )
    
    # IPs bloquées (actuellement)
    blocked_ips = await secure_logger.search_logs(
        event_type="IP_BLOCKED",
        start_time=now - timedelta(minutes=15),
        end_time=now
    )
    
    # Tendance du risque (derniers 7 jours)
    risk_trend = await _calculate_risk_trend(days)
    
    # Événements récents
    recent_events = await secure_logger.search_logs(
        start_time=now - timedelta(hours=1),
        limit=20
    )
    
    return {
        **stats,
        "failed_logins_1h": len(failed_logins),
        "blocked_ips_count": len(set(e["ip_address"] for e in blocked_ips if e["ip_address"])),
        "risk_trend": risk_trend,
        "recent_events": [
            {
                "timestamp": e["timestamp"],
                "event_type": e["event_type"],
                "message": e["message"],
                "risk_score": e["risk_score"],
                "ip_address": e["ip_address"]
            }
            for e in recent_events
        ],
        "suspicious_ips": stats.get("suspicious_ips", [])
    }


@router.get("/events")
async def get_security_events(
    event_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    ip_address: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    min_risk_score: int = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Rechercher les événements de sécurité."""
    # Vérifier les permissions
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    events = await secure_logger.search_logs(
        event_type=event_type,
        user_id=user_id,
        ip_address=ip_address,
        start_time=start_time,
        end_time=end_time,
        min_risk_score=min_risk_score,
        limit=limit
    )
    
    return {
        "events": events,
        "total": len(events),
        "filters": {
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "min_risk_score": min_risk_score
        }
    }


@router.post("/export")
async def export_security_logs(
    start_time: datetime,
    end_time: datetime,
    format: str = Query(default="json", regex="^(json|csv)$"),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Exporter les logs de sécurité."""
    # Vérifier les permissions
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Limiter l'export à 30 jours
    if (end_time - start_time).days > 30:
        raise HTTPException(status_code=400, detail="Export limited to 30 days")
    
    export_file = await secure_logger.export_logs(start_time, end_time, format)
    
    return {
        "message": "Export completed",
        "file": export_file,
        "size_mb": round(len(open(export_file, 'rb').read()) / (1024*1024), 2)
    }


@router.post("/cleanup")
async def cleanup_old_logs(
    days_to_keep: int = Query(default=90, ge=30, le=365),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Nettoyer les anciens logs."""
    # Vérifier les permissions
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    await secure_logger.cleanup_old_logs(days_to_keep)
    
    return {
        "message": f"Logs older than {days_to_keep} days cleaned up"
    }


async def _calculate_risk_trend(days: int) -> Dict[str, Any]:
    """Calculer la tendance du risque."""
    labels = []
    values = []
    
    for i in range(days):
        date = datetime.utcnow() - timedelta(days=days-i-1)
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Calculer le risque moyen pour ce jour
        events = await secure_logger.search_logs(
            start_time=start_of_day,
            end_time=end_of_day,
            limit=10000
        )
        
        if events:
            avg_risk = sum(e["risk_score"] for e in events) / len(events)
        else:
            avg_risk = 0
        
        labels.append(date.strftime("%m/%d"))
        values.append(round(avg_risk, 2))
    
    return {
        "labels": labels,
        "values": values
    }
