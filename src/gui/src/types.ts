export type Medium = 'electric' | 'thermal' | 'monetary' | 'data';

export type AssetType = string;

export type AssetPort = {
  id: string;
  medium: Medium;
  label: string;
  description?: string;
};

export type AssetUiMeta = {
  displayName: string;
  color: string;
  presets: Record<string, Record<string, string | number | boolean>>;
  ports: {
    in: AssetPort[];
    out: AssetPort[];
  };
};

export type ConfigAsset = {
  id: string;
  assetType: AssetType;
  name: string;
  preset: string;
  color: string;
  x: number;
  y: number;
  params: Record<string, string | number | boolean>;
};

export type ConfigPipe = {
  id: string;
  x: number;
  y: number;
  medium: Medium;
  in: string[][];
  out: string[][];
};
