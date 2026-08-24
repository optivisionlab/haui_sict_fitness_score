export interface CheckinImage {
  camera_id: number;
  checkin_time: string;
  image_url: string;
}

export interface CheckinImageResponse {
  count: number;
  images: CheckinImage[];
}
