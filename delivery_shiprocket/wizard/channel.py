# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class ChannelType(models.TransientModel):
    _name = "delivery.channel.shiprocket"
    _description = "Channel from Shiprocket"

    channel_type = fields.Selection(selection="_get_channel_types", string="Channel")
    channel_code = fields.Selection(selection="_get_channel_codes", string="Channel Code", store=True)
    delivery_carrier_id = fields.Many2one('delivery.carrier')

    @api.onchange('channel_type')
    def onchange_channel_type(self):
        """
        Selection of Channel, the Channel code is set based on particular channel.
        """
        if self.channel_type:
            self.channel_code = self.env.context.get('channel_types').get(self.channel_type)

    def _get_channel_types(self):
        """
        Returns the channel name for selection field - channel_type
        """
        if self.env.context.get('channel_types'):
            return [(channel, channel) for channel in self.env.context.get('channel_types').keys()]
        else:
            return []

    def _get_channel_codes(self):
        """
        Returns the channel code for selection field - channel_code
        """
        if self.env.context.get('channel_types'):
            return [(channel, channel) for channel in self.env.context.get('channel_types').values()]
        else:
            return []

    def action_validate(self):
        """
        Change carrier's Channel on click of Select button.
        """
        if self.channel_type and self.delivery_carrier_id:
            self.delivery_carrier_id.shiprocket_channel = self.channel_type
            self.delivery_carrier_id.shiprocket_channel_code = self.channel_code
