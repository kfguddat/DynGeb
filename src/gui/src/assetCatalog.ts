import { AssetUiMeta } from './types';

export const fallbackAssetCatalog: Record<string, AssetUiMeta> = {
  pv: {
    displayName: 'PV',
    color: '#f6bd60',
    presets: {
      Default: {
        capacity_kwp: 10,
        efficiency: 0.18,
        azimuth_deg: 180,
        tilt_deg: 35,
      },
    },
    ports: {
      in: [],
      out: [{ id: 'electricity_out', medium: 'electric', label: 'P_out' }],
    },
  },
  el: {
    displayName: 'Load',
    color: '#84a59d',
    presets: {
      Default: {
        type: 'static',
        load_kw: 1,
      },
    },
    ports: {
      in: [{ id: 'electricity_in', medium: 'electric', label: 'P_in' }],
      out: [
        { id: 'electricity_demand', medium: 'electric', label: 'Demand' },
        { id: 'electricity_unmet', medium: 'electric', label: 'Unmet' },
      ],
    },
  },
  grd: {
    displayName: 'Grid',
    color: '#6d597a',
    presets: {
      Default: {
        type: 'static',
        price_import: 0.25,
        price_export: 0.15,
      },
    },
    ports: {
      in: [{ id: 'electricity_in', medium: 'electric', label: 'Export to Grid' }],
      out: [{ id: 'electricity_out', medium: 'electric', label: 'Import from Grid' }],
    },
  },
};
