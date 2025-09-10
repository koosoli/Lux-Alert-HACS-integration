class LuAlertCard extends HTMLElement {
  set hass(hass) {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: 'open' });
      const card = document.createElement('ha-card');
      card.header = 'LU-Alert';
      this.content = document.createElement('div');
      this.content.className = 'card-content';
      card.appendChild(this.content);
      
      const style = document.createElement('style');
      style.textContent = `
        .no-alerts {
          display: flex;
          align-items: center;
          padding: 16px;
        }
        .no-alerts ha-icon {
          margin-right: 8px;
          color: var(--success-color);
        }
        .alert-container {
          padding: 12px;
          margin-bottom: 8px;
          border-radius: 4px;
          border-left-width: 5px;
          border-left-style: solid;
        }
        .headline {
          font-weight: bold;
          font-size: 1.1em;
          margin-bottom: 4px;
        }
        .details {
          font-size: 0.9em;
          margin-bottom: 8px;
          opacity: 0.8;
        }
        .description {
          font-size: 1em;
          line-height: 1.4;
        }
        .severity-information { border-color: #607d8b; }
        .severity-minor { border-color: #ffc107; }
        .severity-moderate { border-color: #ff9800; }
        .severity-severe { border-color: #f44336; }
        .severity-extreme { border-color: #b71c1c; }
        .severity-unknown { border-color: var(--disabled-text-color); }
        .severity-none { border-color: var(--disabled-text-color); }
      `;
      
      this.shadowRoot.append(style, card);
    }

    const entityId = this.config.entity || 'sensor.lu_alert';
    const state = hass.states[entityId];

    if (!state) {
      this.content.innerHTML = `
        <div class="no-alerts">
          <span>Entity not found: ${entityId}</span>
        </div>
      `;
      return;
    }

    const alerts = state.attributes.alerts || [];

    if (alerts.length === 0) {
      this.content.innerHTML = `
        <div class="no-alerts">
          <ha-icon icon="mdi:shield-check"></ha-icon>
          <span>No active alerts matching your criteria.</span>
        </div>
      `;
    } else {
      this.content.innerHTML = alerts.map(alert => `
        <div class="alert-container severity-${alert.severity.toLowerCase()}">
          <div class="headline">${alert.headline}</div>
          <div class="details">
            <strong>Severity:</strong> ${alert.severity} | <strong>Event:</strong> ${alert.event}
          </div>
          <div class="description">${alert.description.replace(/<[^>]*>?/gm, '')}</div>
        </div>
      `).join('');
    }
  }

  setConfig(config) {
    this.config = config;
  }

  getCardSize() {
    return 3;
  }
}

customElements.define('lu-alert-card', LuAlertCard);
