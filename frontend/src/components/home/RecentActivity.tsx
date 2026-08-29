import React from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import { formatTimeBst } from '../../utils/formatting';
import type { EventItem } from '../../types';

interface Props {
  events: EventItem[];
  onNavigateActivity?: () => void;
}

export const RecentActivity: React.FC<Props> = ({ events, onNavigateActivity }) => {
  return (
    <div className="recent-activity-card glass">
      <div className="sect-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="sect-label">Recent Activity</span>
          <DataHonestyTag type="MEASURED" size="sm" tooltip="Local audit trail of commands and physical relay confirmations" />
        </div>
        {onNavigateActivity && (
          <button className="btn-link" onClick={onNavigateActivity}>
            View all →
          </button>
        )}
      </div>

      {events.length === 0 ? (
        <div className="activity-empty-state">
          <span className="empty-icon">📋</span>
          <strong>No events yet</strong>
          <p>Relay switching commands and system confirmations will be recorded here.</p>
        </div>
      ) : (
        <div className="activity-list">
          {events.slice(0, 5).map((item) => (
            <div key={item.id} className="activity-row">
              <span className={`activity-icon-badge badge-${item.type}`}>
                {item.type === 'command' ? '⚡' : item.type === 'confirm' ? '✓' : 'ℹ'}
              </span>
              <div className="activity-details">
                <strong>{item.title}</strong>
                <span>{item.detail}</span>
              </div>
              <time className="activity-time">{formatTimeBst(item.ts)}</time>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
