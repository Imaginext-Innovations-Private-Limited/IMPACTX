import math
import copy

import torch
import torch.nn as nn
import torch.nn.functional as F

from torchvision.models import mobilenet_v3_large


class ResidualFeatureExtractor(nn.Module):
    def __init__(self):
        super().__init__()

        self.residual_conv = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),

            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),

            nn.MaxPool2d(2),

            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),

            nn.AdaptiveAvgPool2d((1, 1))
        )

        self.output_layer = nn.Linear(128, 256)

    def forward(self, images):
        gray = images.mean(dim=1, keepdim=True)

        blurred = F.avg_pool2d(
            gray, kernel_size=5, stride=1, padding=2
        )

        residual = gray - blurred
        features = self.residual_conv(residual)
        features = features.flatten(1)

        return self.output_layer(features)


class DifferentiableFrequencyExtractor(nn.Module):
    def __init__(self):
        super().__init__()

        s = 1.0 / math.sqrt(2.0)

        haar_filters = torch.tensor([
            [[s*s,  s*s], [s*s,  s*s]],
            [[s*s, -s*s], [s*s, -s*s]],
            [[s*s,  s*s], [-s*s, -s*s]],
            [[s*s, -s*s], [-s*s,  s*s]]
        ], dtype=torch.float32).unsqueeze(1)

        self.register_buffer("haar_filters", haar_filters)

    def haar_transform(self, x):
        return F.conv2d(x, self.haar_filters, stride=2)

    def forward(self, images):
        gray = images.mean(dim=1, keepdim=True)

        fft = torch.fft.fft2(gray)
        fft = torch.fft.fftshift(fft, dim=(-2, -1))
        fft_features = torch.log1p(torch.abs(fft))

        level1 = self.haar_transform(gray)
        ll1 = level1[:, 0:1]
        detail1 = level1[:, 1:4]

        level2 = self.haar_transform(ll1)
        ll2 = level2[:, 0:1]
        detail2 = level2[:, 1:4]

        haar_features = torch.cat([
            ll2.flatten(1),
            detail2.flatten(1),
            detail1.flatten(1)
        ], dim=1)

        return fft_features, haar_features


class FrequencyEncoder(nn.Module):
    def __init__(self):
        super().__init__()

        self.fft_encoder = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),

            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),

            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(64, 128),
            nn.ReLU(inplace=True)
        )

        self.haar_encoder = nn.Sequential(
            nn.Linear(25600, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(512, 128),
            nn.ReLU(inplace=True)
        )

        self.fusion = nn.Sequential(
            nn.Linear(256, 256),
            nn.ReLU(inplace=True)
        )

    def forward(self, fft_features, haar_features):
        fft_vector = self.fft_encoder(fft_features)
        haar_vector = self.haar_encoder(haar_features)

        combined = torch.cat([fft_vector, haar_vector], dim=1)
        return self.fusion(combined)


class DegradationConditionedReliability(nn.Module):
    def __init__(self, descriptor_dim=8, hidden_dim=64):
        super().__init__()

        self.reliability_network = nn.Sequential(
            nn.Linear(descriptor_dim, hidden_dim),
            nn.ReLU(inplace=True),

            nn.Linear(hidden_dim, 32),
            nn.ReLU(inplace=True),

            nn.Linear(32, 3),
            nn.Sigmoid()
        )

    def forward(self, degradation_descriptors):
        return self.reliability_network(degradation_descriptors)


class ReliabilityWeightedFusion(nn.Module):
    def __init__(self, feature_dim=256):
        super().__init__()

        self.spatial_projection = nn.Sequential(
            nn.Linear(960, feature_dim),
            nn.LayerNorm(feature_dim),
            nn.ReLU(inplace=True)
        )

        self.frequency_projection = nn.Sequential(
            nn.Linear(256, feature_dim),
            nn.LayerNorm(feature_dim),
            nn.ReLU(inplace=True)
        )

        self.residual_projection = nn.Sequential(
            nn.Linear(256, feature_dim),
            nn.LayerNorm(feature_dim),
            nn.ReLU(inplace=True)
        )

    def forward(self, features, reliability_scores):
        spatial = self.spatial_projection(features["spatial"])
        frequency = self.frequency_projection(features["frequency"])
        residual = self.residual_projection(features["residual"])

        nodes = torch.stack(
            [spatial, frequency, residual], dim=1
        )

        return nodes * reliability_scores.unsqueeze(-1)


class MultiHeadGraphAttention(nn.Module):
    def __init__(self, feature_dim=256, num_heads=4):
        super().__init__()

        assert feature_dim % num_heads == 0

        self.feature_dim = feature_dim
        self.num_heads = num_heads
        self.head_dim = feature_dim // num_heads

        self.query = nn.Linear(feature_dim, feature_dim)
        self.key = nn.Linear(feature_dim, feature_dim)
        self.value = nn.Linear(feature_dim, feature_dim)

        self.output_projection = nn.Linear(feature_dim, feature_dim)
        self.norm = nn.LayerNorm(feature_dim)
        self.scale = self.head_dim ** -0.5

    def forward(self, nodes):
        batch_size, num_nodes, _ = nodes.shape

        Q = self.query(nodes)
        K = self.key(nodes)
        V = self.value(nodes)

        Q = Q.view(
            batch_size, num_nodes, self.num_heads, self.head_dim
        ).transpose(1, 2)

        K = K.view(
            batch_size, num_nodes, self.num_heads, self.head_dim
        ).transpose(1, 2)

        V = V.view(
            batch_size, num_nodes, self.num_heads, self.head_dim
        ).transpose(1, 2)

        scores = torch.matmul(Q, K.transpose(-2, -1)) * self.scale
        attention = torch.softmax(scores, dim=-1)

        attended = torch.matmul(attention, V)
        attended = attended.transpose(1, 2).contiguous()
        attended = attended.view(
            batch_size, num_nodes, self.feature_dim
        )

        output = self.output_projection(attended)
        output = self.norm(output + nodes)

        return output, attention


class AdaptiveBranchGating(nn.Module):
    def __init__(self, feature_dim=256, hidden_dim=128):
        super().__init__()

        self.gate_network = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim),
            nn.ReLU(inplace=True),

            nn.Linear(hidden_dim, 64),
            nn.ReLU(inplace=True),

            nn.Linear(64, 1)
        )

    def forward(self, graph_nodes):
        gate_logits = self.gate_network(graph_nodes).squeeze(-1)
        gate_weights = torch.softmax(gate_logits, dim=1)

        fused_features = torch.sum(
            graph_nodes * gate_weights.unsqueeze(-1), dim=1
        )

        return fused_features, gate_weights


class AMSFClassifier(nn.Module):
    def __init__(self, input_dim=256, num_classes=2):
        super().__init__()

        self.classifier = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),

            nn.Linear(64, num_classes)
        )

    def forward(self, fused_features):
        return self.classifier(fused_features)


class AMSFGNetV2(nn.Module):
    def __init__(
        self,
        spatial_backbone,
        frequency_extractor,
        frequency_encoder,
        residual_extractor,
        use_reliability=True
    ):
        super().__init__()

        self.use_reliability = use_reliability

        self.spatial = spatial_backbone
        self.frequency_extractor = frequency_extractor
        self.frequency_encoder = frequency_encoder
        self.residual = residual_extractor

        self.register_buffer(
            "imagenet_mean",
            torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        )

        self.register_buffer(
            "imagenet_std",
            torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
        )

        self.reliability = DegradationConditionedReliability(
            descriptor_dim=8, hidden_dim=64
        )

        self.reliability_fusion = ReliabilityWeightedFusion(
            feature_dim=256
        )

        self.graph_attention = MultiHeadGraphAttention(
            feature_dim=256, num_heads=4
        )

        self.adaptive_gating = AdaptiveBranchGating(
            feature_dim=256, hidden_dim=128
        )

        self.classifier = AMSFClassifier(
            input_dim=256, num_classes=2
        )

    def forward(self, raw_images, degradation_descriptors):
        normalized_images = (
            raw_images - self.imagenet_mean
        ) / self.imagenet_std

        spatial_features = self.spatial(normalized_images)

        fft_features, haar_features = self.frequency_extractor(
            raw_images
        )

        frequency_features = self.frequency_encoder(
            fft_features, haar_features
        )

        residual_features = self.residual(raw_images)

        branch_features = {
            "spatial": spatial_features,
            "frequency": frequency_features,
            "residual": residual_features
        }

        if self.use_reliability:
            reliability_scores = self.reliability(
                degradation_descriptors
            )
        else:
            reliability_scores = torch.ones(
                raw_images.size(0),
                3,
                device=raw_images.device,
                dtype=raw_images.dtype
            )

        nodes = self.reliability_fusion(
            branch_features, reliability_scores
        )

        graph_nodes, graph_attention_weights = self.graph_attention(
            nodes
        )

        fused_features, gate_weights = self.adaptive_gating(
            graph_nodes
        )

        logits = self.classifier(fused_features)

        return {
            "logits": logits,
            "reliability_scores": reliability_scores,
            "graph_attention": graph_attention_weights,
            "gate_weights": gate_weights,
            "fused_features": fused_features
        }


def build_model_b():
    spatial_backbone = mobilenet_v3_large(weights=None)
    spatial_backbone.classifier = nn.Identity()

    return AMSFGNetV2(
        spatial_backbone=spatial_backbone,
        frequency_extractor=DifferentiableFrequencyExtractor(),
        frequency_encoder=FrequencyEncoder(),
        residual_extractor=ResidualFeatureExtractor(),
        use_reliability=False
    )
